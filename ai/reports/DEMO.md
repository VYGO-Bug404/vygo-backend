# Demo Nivel 1 -- Monterrey real con navegación A* propia

Este documento se va llenando fase por fase (ver `ai/docs/NIVEL-1-DEMO-MTY.md`).

## Fase A -- Replay (`ai/scripts/build_replay.py`)

Reproduce el turno congelado seed 10000 (escenario índice 0 de `scenarios/test_30.pkl`,
120 min, evento SURGE al minuto 60) bajo `B_SERIAL` y `B2`, reutilizando
`vygo.evaluate.correr_escenario_con_paradas` -- el mismo mecanismo que produjo los
números oficiales de `reports/EVAL.md` -- y lo vuelca a `demo/replay.json`.

**Compuerta A: PASA.**

| Política | total_mxn (JSON) | total_mxn (EVAL.md) | entregas (JSON) | entregas (EVAL.md) |
|---|---|---|---|---|
| B_SERIAL | 253.95 | 253.95 | 5 | 5 |
| B2 (vygo) | 888.74 | 888.74 | 16 | 16 |

Los cuatro números coinciden exactos.

## Reproducibilidad -- hallazgo completo

**El hallazgo, resumido:** cualquier instrumentación dentro del hot path de simulación
(incluso de sólo lectura, sin mutar estado) puede cambiar el resultado del turno, porque
`sequencer.held_karp` acota su enumeración exacta con un presupuesto de **reloj de
pared**, no de tiempo de CPU ni de pasos. `reports/EVAL.md` ya documentaba esto para
contención de CPU externa (otra sesión entrenando en la misma máquina); esta tarea
encontró que el mismo mecanismo se dispara con el overhead de instrumentación propio del
script, sin ningún proceso externo de por medio.

**Cómo se descubrió, paso a paso:**

1. Primer intento de `build_replay.py`: para separar eventos `MOVE`/`WAIT`, se envolvía
   `env._procesar_llegada_nodo` (monkeypatch de instancia, nunca de clase) recalculando
   el tramo de viaje puro con `env._travel_fn(pos_actual, parada.pos, env.t)`. Esa
   versión reprodujo 253.95/5 y 888.74/16 exactos -- pasó la Compuerta A.
2. Antes de confiar en ese resultado, se verificó si el recálculo de "tramo puro" era
   correcto comparándolo contra el calendario real del simulador. No lo era: se
   encontraron discrepancias (`gap`) de hasta **-399 segundos** entre lo recalculado y lo
   que el simulador realmente había programado -- porque `sequencer._simular_adelante`
   calendariza cada tramo con el `t`/`pos` vigentes **al momento de calendarizar**, no al
   momento en que el vehículo de verdad llega (pueden diferir si hubo un
   `reposicionarse` de por medio).
3. Se corrigió para leer `env._llegadas_cache[0]` en vivo -- el valor que el simulador
   YA calculó y tiene cacheado, no uno recalculado por el script (más alineado con
   "reusar, no inventar"). Con ese cambio -- que sólo toca CÓMO se lee un dato para
   clasificar eventos, sin tocar la política ni el entorno, y sin ninguna escritura --
   el resultado de VYGO **cambió** a **737.39 MXN / 13 entregas** (antes 888.74/16).
   B_SERIAL no cambió (253.95/5 en ambas versiones -- su plan nunca crece más allá de 1
   pedido, así que el camino exacto de `held_karp` es trivial y no se acerca al
   presupuesto de 25 ms).

**Números concretos medidos:**

| Versión de `_procesar_llegada_nodo` | VYGO total_mxn | VYGO entregas | B_SERIAL total_mxn | B_SERIAL entregas |
|---|---|---|---|---|
| Envuelta, recalculando con `_travel_fn` | 888.74 | 16 | 253.95 | 5 |
| Envuelta, leyendo `_llegadas_cache[0]` | 737.39 | 13 | 253.95 | 5 |
| Sin envolver (`correr_escenario_con_paradas` tal cual) | 888.74 | 16 | 253.95 | 5 |

**Por qué pasa esto:** `sequencer._LIMITE_TIEMPO_EXACTO_S = 0.025` (25 ms), medido con
`time.perf_counter()` dentro de `held_karp`, acota cuántas de las (hasta 90, con 3
pedidos) secuencias válidas por precedencia se alcanzan a evaluar exactamente antes de
conformarse con la mejor encontrada hasta ese punto (siempre verificada factible, nunca
viola frescura -- pero no necesariamente óptima). Ese presupuesto se mide en tiempo de
**reloj real transcurrido**, no en pasos ni en tiempo de CPU del proceso. Cualquier
código adicional que se ejecute alrededor de las llamadas a `held_karp` -- así sea una
sola lectura de lista en vez de una llamada a función, ambas sin efectos secundarios --
desplaza en qué punto exacto se agota ese reloj, cambiando qué secuencias se alcanzan a
evaluar, lo que cambia la ruta elegida, lo que cambia cuánto tiempo real transcurre para
llegar a cada parada, lo que en cascada cambia qué ofertas ve el agente después. En 120
minutos simulados con docenas de recalendarizaciones, ese efecto se acumula en un
resultado financiero distinto -- no es ruido de redondeo, es una ruta y un conjunto de
pedidos entregados genuinamente diferente (13 vs 16).

**Por qué `build_replay.py` no envuelve nada:** es la única forma verificada de
reproducir los cuatro números oficiales exactos. `ai/scripts/build_replay.py` llama
`vygo.evaluate.correr_escenario_con_paradas` **tal cual**, sin monkeypatch de ninguna
clase ni instancia. `MOVE` y `WAIT` no son eventos en `replay.json` por esta misma razón:

- `MOVE` se deriva de posiciones consecutivas ya devueltas en `paradas` (Fase D ya hace
  esto para trazar A* entre paradas consecutivas).
- `WAIT` se deriva en la Fase E, al pintar, con:
  `espera_s = (t_llegada[i+1] - t_llegada[i]) - segundos_de_Astar[i -> i+1]`. Si es
  positiva, el repartidor llega y se queda parado (esperando la comida en el
  restaurante); si es `<=0`, viaja todo el tramo. Cero instrumentación, cero riesgo.

**`replay.json` queda CONGELADO.** No se regenera. Correr `build_replay.py` de nuevo --
en esta máquina o en otra -- puede dar números distintos por este mismo presupuesto de
reloj de pared, y eso rompería la coherencia con `reports/EVAL.md` y con el pitch.
Commiteado en `c4e3322` (`ai/demo/replay.json`, `ai/scripts/build_replay.py`).

**Segunda evidencia independiente, encontrada ya construida en el repo:**
`ai/demo/turno_datos.json` (generado por `vygo/generar_demo.py`, para el visualizador
canvas que ya existía antes de esta tarea) trae **B2 = 875.27 MXN** -- misma política,
mismo escenario congelado (seed 10000), corrida distinta a la de `EVAL.md`/`replay.json`
(888.74 MXN) y distinta también a la corrida intermedia con `_llegadas_cache` en vivo
(737.39 MXN). Tres corridas, tres números, mismo escenario, misma política -- confirma
que el efecto no es un artefacto de este script en particular: es el presupuesto de
reloj de pared de `held_karp`, disparado por CUALQUIER instrumentación alrededor del
loop de decisión, venga de donde venga.

| Origen | B2 total_mxn |
|---|---|
| `reports/EVAL.md` / `demo/replay.json` (congelado, oficial) | 888.74 |
| `build_replay.py`, versión con `_llegadas_cache[0]` en vivo (descartada) | 737.39 |
| `demo/turno_datos.json` (`vygo/generar_demo.py`, visualizador preexistente) | 875.27 |

**Consecuencia que se queda escrita aquí:** `turno_datos.json` **NO es fuente de verdad
para totales** -- nunca lo fue, y menos ahora que se entiende por qué. La única fuente
de verdad de totales es `demo/replay.json` congelado (y, detrás de él, `reports/EVAL.md`,
inmutable). De `vygo/generar_demo.py` y su plantilla (`demo/_plantilla_turno.html`) en la
Fase E sólo se van a reusar **fórmulas y redacción** (cómo arma el texto de una decisión,
cómo dibuja la barra de frescura, la estructura de controles) -- **nunca sus números**.

## Decisión de diseño -- `decisiones` vacío en `replay.json`, se reconstruye en Fase D

`replay.json` trae `"decisiones": []` para ambas políticas. **No es un pendiente sin
resolver, es la decisión correcta dado el hallazgo de arriba:** el riesgo de timing
existe SÓLO mientras el simulador corre bajo el presupuesto de 25 ms de reloj de pared
de `held_karp`. En frío, sobre el plan YA CONGELADO (sin el simulador corriendo, sin ese
reloj), no hay riesgo -- así que el trío de decisión se reconstruye post-hoc en
`ai/scripts/build_nav.py` (Fase D), no en `build_replay.py`.

**Plan para Fase D (anotado aquí, NO implementado todavía):**

Para cada pedido **ACEPTADO** en el plan congelado de cada política:

- `delta_f` = el pago real de ese pedido (ya está en `replay.json`, campo `pago_mxn` de
  su evento `D`).
- `delta_t` = (minutos del plan **CON** ese pedido) − (minutos del plan **SIN** él),
  calculado con los tiempos reales de A* sobre la secuencia congelada -- sin correr el
  entorno.
- `rho_ref` = tasa **realizada** del turno completo = `total_mxn / horas`:
  - B2: 888.74 / 2 = **444.37 MXN/h**
  - B_SERIAL: 253.95 / 2 = **126.98 MXN/h**

  Esto no es un atajo: la regla de umbral del modelo es precisamente aceptar cuando la
  tasa marginal supera la tasa promedio acumulada -- usar la tasa realizada del turno es
  el enunciado correcto de la regla, no una aproximación.
- `ratio` = `(delta_f - c_kappa*delta_delta) / delta_t`.

Los pedidos **RECHAZADOS no son recuperables post-hoc** -- no se sabe qué otras ofertas
aparecieron en cada ronda que se perdió. El panel de la Fase E mostrará **sólo
aceptaciones**, y lo dirá explícitamente ("economía de cada aceptación"). No se van a
inventar rechazos para completar el panel.

## Fase B -- Grafo vial (`ai/nav/grafo.py`)

Descarga (con cache) el grafo `drive` de OSMnx sobre `BBOX_MTY`, con `speed_kph` y
`travel_time` (segundos) imputados. **Compuerta B: PASA** -- 15007 nodos, 36547 aristas,
18.97 MB, `velocidad_maxima_ms=25.00` (90 km/h).

**Bloqueo y arreglo de infraestructura, no de código:** la primera corrida falló con
`SSLCertVerificationError` contra Overpass -- confirmado que era un problema general de
la máquina (hasta `pypi.org` fallaba igual), causado por un proxy que intercepta HTTPS
con una CA que Windows ya conoce pero que el bundle embebido de `certifi` no trae. Se
resolvió con `truststore.inject_into_ssl()` al inicio del módulo (antes de importar
`osmnx`), que hace que `ssl`/`requests` usen el almacén de certificados del sistema
operativo en vez del bundle de `certifi` -- la verificación de certificados sigue
activa, sólo cambia de dónde salen las CAs de confianza. No se desactivó verificación
SSL en ningún momento.

**Hallazgo -- el grafo completo NO es ruteable de punta a punta.** 125 componentes
fuertemente conexas; la mayor cubre 14690 de 15007 nodos (97.9%), el resto son
fragmentos sin camino de vuelta (calles de un solo sentido cortadas por el bbox). Se
agregó `cargar_grafo_ruteable()` -- recorta al mayor componente fuertemente conexo -- y
es la única versión que se usa para `nearest_nodes`/A* de aquí en adelante.

## Fase C -- A* propio (`ai/nav/astar.py`)

`heuristica_tiempo` = haversine/`v_max_ms`, admisible por construcción (ningún tramo
real puede ser más rápido que ir en línea recta a la velocidad máxima del grafo).
**Compuerta C: PASA** -- 3/3 pruebas, sobre 30 pares aleatorios (semilla 42) del grafo
ruteable (14690 nodos): conexo, `segundos` coincide con Dijkstra dentro de 0.1% (0.0000%
de desviación peor caso, 0/30 fuera de tolerancia), polilínea con al menos tantos puntos
como nodos.

A* salió más rápido que Dijkstra (30.38 ms vs 31.88 ms) pero con un margen mucho más
chico que el medido en otra corrida con otra semilla (~22 ms vs ~31 ms, ~29% más rápido)
-- razón estructural, no un problema: `v_max_ms` corresponde a 90 km/h pero la velocidad
típica del grafo ronda los 35 km/h, así que la heurística subestima el costo real por
~2.5x y poda poco. Es el precio de mantenerla admisible; nada que arreglar.

## Fase D -- Proyección, geometría real y decisiones reconstruidas

`ai/vygo/geo_mty.py` (nuevo, aislado -- no importa ni modifica `geo.py`): transformación
afín rejilla -> (lat, lon), ancla en la esquina SW de `BBOX_MTY`, con un `assert` de
sanidad que corre al importar el módulo (distancia haversine entre celdas adyacentes
proyectadas vs `escala_km_por_celda`, dentro de 2%) -- pasa con la escala real de este
proyecto (0.5 km/celda).

`ai/scripts/build_nav.py` proyecta las 42 paradas congeladas (10 de serial + 32 de
vygo), las pega al grafo ruteable en una sola llamada a `nearest_nodes`, corre A* real
entre cada par de paradas consecutivas (cacheado por par de nodos), y escribe
`demo/geometria.json`.

**Snap:** las 42 paradas quedaron a menos de 300 m de su nodo más cercano (máximo
observado: 202.2 m). Ninguna cayó fuera de la traza vial.

**Compuerta D1: PASA.** 40/40 pares resueltos (0% sin resolver).

| Política | km reales totales | minutos reales (A*) | km reales por entrega |
|---|---|---|---|
| B_SERIAL | 45.52 | 53.5 | **9.10** |
| B2 (vygo) | 66.73 | 80.7 | **4.17** |

`ms_por_consulta` (A*, sobre las consultas nuevas, no cacheadas): **7.36 ms**.

**El número de gasolina del pitch:** B2 gasta más del doble de km totales que B_SERIAL
(66.73 vs 45.52) pero **menos de la mitad de km por entrega** (4.17 vs 9.10) -- agrupar
significa manejar más en total porque se entrega más, pero cada entrega individual sale
más barata en combustible. Es la misma historia que ya contaba `reports/EVAL.md`
(rho, entregados) contada ahora en kilómetros reales sobre calles reales.

### Decisiones reconstruidas (D.3)

**Compuerta D2: PASA.** `decisiones(serial)=5=entregas`, `decisiones(vygo)=16=entregas`.
Sin anomalías (`delta_min<=0` o `tasa_marginal<0`) en ninguna de las 21 aceptaciones.
`c_kappa` = `vygo.env.COSTO_KM_MXN` (`env.py:56`, "combustible + mantenimiento,
aproximado") = **1.2 MXN/km** -- leído de la constante real, no inventado.
`demo/replay.json` se actualizó IN PLACE, sólo el campo `"decisiones"` -- verificado con
un hash de todo lo demás antes/después: idéntico byte a byte.

**Serial** (rho_hat = 126.98 MXN/h):

| pedido | tasa_marginal MXN/h |
|---|---|
| p12 | 231.7 |
| p1242 | 313.9 |
| p3311 | 122.0 |
| p5911 | 159.9 |
| p7894 | 165.7 |

**Vygo** (rho_hat = 444.37 MXN/h):

| pedido | tasa_marginal MXN/h |
|---|---|
| p12 | 388.0 |
| p40 | 1532.1 |
| p17 | 843.4 |
| p210 | 3805.7 |
| p2132 | 567.8 |
| p2801 | 6863.0 |
| p2135 | 1724.9 |
| p2800 | 446.5 |
| p4036 | 580.2 |
| p4508 | 395.7 |
| p5340 | 458.0 |
| p5733 | 4350.5 |
| p6250 | 352.9 |
| p8183 | 775.2 |
| p9059 | 985.4 |
| p9058 | 1011.8 |

**Observación honesta, no una anomalía que detenga nada (ambas cantidades salieron
positivas, Compuerta D2 pasa tal cual está definida):** varias `tasa_marginal` de VYGO
son enormes (hasta $6863/h, muy por encima de `rho_hat`=444/h). Es consistencia
matemática de la fórmula, no un error: cuando B2 agrupa pedidos, insertar UNO más en una
ruta que ya iba a pasar por ahí cuesta unos pocos minutos reales de más (`delta_min`
chico) -- extrapolar ese costo marginal minúsculo a una tasa "por hora" completa infla
el número. Son casos de agrupamiento muy eficiente, no un bug en el cálculo. Se reporta
tal cual, sin suavizar ni recortar los extremos (el dato completo queda intacto en
`replay.json`; en la Fase E el titular se topa visualmente en pantalla a partir de
$2000/h -- ver esa sección -- pero el JSON nunca se toca).

### Validación cruzada -- dos geometrías independientes, misma conclusión

`reports/EVAL.md` (unidades de rejilla, sin calles reales) ya daba km por entrega de
**6.53 -> 3.42** (B_SERIAL -> B2), razón 3.42/6.53 = **0.524**. El A* sobre calles reales
de Monterrey (esta fase) da **9.10 -> 4.17**, razón 4.17/9.10 = **0.458**. Dos
geometrías completamente independientes -- una abstracta sobre la rejilla del
simulador, otra sobre el grafo vial real con sentidos únicos y distancias reales -- ,
calculadas con código distinto, llegan a la MISMA conclusión cualitativa (VYGO gasta
menos por entrega), y la geometría real la favorece incluso MÁS (razón menor: 0.458 <
0.524). Esto es **corroboración del resultado, no coincidencia** -- si el efecto fuera
un artefacto de cómo el simulador abstracto mide distancias, no tendría por qué
sobrevivir, y mucho menos reforzarse, al proyectarlo sobre calles reales con giros,
sentidos únicos y rutas que la rejilla nunca modeló.

**Aclaración explícita, para que nadie lea la tabla al revés:** B2 recorre MÁS
kilómetros TOTALES que B_SERIAL (66.73 km vs 45.52 km) -- pero es porque hace 16
entregas en vez de 5, no porque sea menos eficiente. La métrica que importa para
"gasto de gasolina" es **km por entrega**, no km totales: ahí B2 gana con claridad
(4.17 vs 9.10).
