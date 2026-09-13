# NIVEL 1 — Demo pareada sobre Monterrey real con navegación A* propia

**Este documento reemplaza por completo a `BLOQUE-B-MTY.md` y `BLOQUE-B3-ASTAR.md`.**
No corras aquellos. Pega este completo en la terminal de Claude Code que trabaja en `ai/`.

---

Estás en el monorepo VYGO, rama `ai/rl-agent`. Lee `ai/CLAUDE.md` antes de escribir
una sola línea.

El entrenamiento y la evaluación **ya terminaron**. Las cifras oficiales viven en
`ai/reports/EVAL.md` y son inmutables. Tu trabajo no es mejorar el agente: es
**construir la demo visual** que muestra lo que el agente ya hace, sobre el mapa real
de Monterrey, con navegación por calles.

---

## 0. Restricciones absolutas

Violar cualquiera de estas invalida las cifras del pitch o rompe el trabajo de otra
sesión que comparte la rama.

**Congelado — no modificar, solo leer:**
`ai/vygo/geo.py`, `ai/vygo/sequencer.py`, `ai/vygo/env.py`, `ai/vygo/generator.py`,
`ai/vygo/policies/*`, `ai/train_ppo.py`, `ai/bc.py`, `ai/policy_net.py`,
`ai/checkpoints/`, `ai/reports/status.json`, `ai/reports/train_log.jsonl`,
`ai/reports/EVAL.md`.

**Prohibido tocar (es del equipo de front):**
`src/`, `package.json`, `index.html`, `vite.config.ts`, `tailwind.config.js`.
Puedes LEERLOS (vas a necesitar la API key de MapTiler). Nunca corras `npm`, `npx`
ni `vite`.

**Archivos nuevos, únicamente estos:**
```
ai/nav/__init__.py
ai/nav/grafo.py
ai/nav/astar.py
ai/nav/test_astar.py
ai/nav/cache/            (gitignored)
ai/vygo/geo_mty.py       (módulo nuevo, NO modifica geo.py)
ai/scripts/build_replay.py
ai/scripts/build_nav.py
ai/demo/turno.html
ai/demo/replay.json
ai/demo/geometria.json
ai/reports/DEMO.md
```

**Entorno:** Windows 10, PowerShell. Nada de `make`. Todo comando que me reportes
debe ser copy-paste directo en PowerShell.

**Git:** rama `ai/rl-agent`. Commits con rutas explícitas
(`git add ai/nav ai/demo ai/scripts`). **Nunca `git add -A`** — hay otra sesión
trabajando en la misma rama. Nunca commits en `main`.

---

## 1. Objetivo

Un archivo `ai/demo/turno.html` que se abra con **doble clic**, sin servidor, y muestre
lado a lado el mismo turno (escenario **seed 10000**, 120 min) bajo dos políticas:

| Panel | Política | Resultado esperado |
|---|---|---|
| Izquierda — "SIN VYGO" | `B_SERIAL` | 5 entregas, $253.95 |
| Derecha — "CON VYGO" | `B2` | 16 entregas, $888.74 |

Un solo reloj maestro controla ambos. Sobre mapa real de Monterrey (MapTiler), con
las rutas siguiendo calles reales calculadas por un A* propio.

**La arquitectura que estás implementando, y que debe quedar visible en el código:**

```
CAPA DE DESPACHO  (ya existe, congelada)
    el agente decide qué pedidos acepta y en qué ORDEN los visita
    output: lista ordenada de IDs de parada
              ↓
CAPA DE NAVEGACIÓN  (esto es lo que construyes)
    A* sobre el grafo vial de OpenStreetMap traza el CAMINO entre paradas consecutivas
    output: polilínea + metros + segundos reales
              ↓
CAPA DE PRESENTACIÓN
    MapLibre dibuja ambas cosas sobre tiles de MapTiler
```

El agente **nunca** llama a A* dentro de su ciclo de decisión. Eso es deliberado: el
secuenciador evalúa miles de secuencias por paso (p95 = 1.04 ms) y un A* cuesta 10–50 ms.
En el Nivel 1 A* corre **en build time**, sobre un replay ya fijo.

---

## 2. Orden de ejecución y compuertas

Son cinco fases. **Cada compuerta es un alto obligatorio.** Si una falla, para y
repórtame el número exacto que salió mal — no improvises un arreglo ni sigas a la
siguiente fase.

---

### FASE A — Replay (`ai/scripts/build_replay.py`)

Reproduce el turno sin tocar el entorno. Instancia el escenario **seed 10000** y corre
`B_SERIAL` y `B2` exactamente como lo hace el evaluador existente (lee cómo lo hace y
reutilízalo; no escribas un loop de evaluación nuevo).

Registra por cada evento:
```
t_min, tipo ('P'|'D'|'MOVE'|'WAIT'), pedido_id, celda_x, celda_y,
pago_mxn|null, frescura_restante_min|null
```

Y en cada **cierre de ronda con decisión**, el trío que la política ya calcula:
```
delta_f, delta_t, ratio = (delta_f - c_kappa*delta_delta)/delta_t,
rho_ref, aceptado (bool), p_gana, anillo
```

Escribe `ai/demo/replay.json`:

```json
{
  "meta": {"seed": 10000, "duracion_min": 120, "theta_min": 25, "surge_min": 60,
           "escala_km_por_celda": <LEER del generador, no inventar>},
  "serial": {"paradas": [...], "decisiones": [...], "total_mxn": 253.95, "entregas": 5},
  "vygo":   {"paradas": [...], "decisiones": [...], "total_mxn": 888.74, "entregas": 16}
}
```

> ### 🚦 COMPUERTA A
> Imprime `total_mxn` y `entregas` de cada política.
> **Si no son exactamente 253.95 / 5 y 888.74 / 16, PARA y repórtame la diferencia.**
> Significa que el replay no reproduce la evaluación oficial, y una demo que muestra
> números distintos a `EVAL.md` es peor que no tener demo.

---

### FASE B — Grafo vial (`ai/nav/grafo.py`)

```powershell
pip install osmnx networkx
```

OSMnx 2.x. Si la instalación falla por geopandas, **repórtalo y para** — no intentes
compilar nada desde fuente.

```python
BBOX_MTY = (-100.360, 25.630, -100.240, 25.720)  # (izq, abajo, der, arriba)
RUTA_CACHE = "ai/nav/cache/mty_drive.graphml"
```

Este bbox cubre Centro, Barrio Antiguo, Obispado y Mitras: zona densa en restaurantes
y **casi toda del mismo lado del río Santa Catarina**, lejos de la Loma Larga. Esto
elimina por construcción el problema de rutas que cruzan donde no hay puente. No lo
cambies sin avisarme.

```python
def cargar_grafo():
    """Si existe el cache lo carga; si no, lo descarga y lo guarda."""
```

Al descargar, en este orden:
1. `ox.graph_from_bbox(BBOX_MTY, network_type="drive")` — `drive` respeta sentidos
   únicos, que en el centro de Monterrey importan muchísimo.
2. `ox.routing.add_edge_speeds(G)` — imputa `speed_kph` por tipo de vía.
3. `ox.routing.add_edge_travel_times(G)` — crea `travel_time` en **segundos**.
4. `ox.io.save_graphml(G, RUTA_CACHE)`.

Expón también:
```python
def velocidad_maxima_ms(G) -> float:
    """Máximo de speed_kph sobre todas las aristas, convertido a m/s."""
```

> ### 🚦 COMPUERTA B
> Imprime nodos, aristas y MB del `.graphml`.
> **Corre esta fase SOLA y primero.** OSMnx pega a la API de Overpass, que se cae o
> te limita sin avisar. Una vez cacheado el archivo, todo lo demás es offline.
> - Si Overpass falla o te rate-limitea: **no reintentes en bucle.** Repórtalo y para.
> - Si el grafo tiene menos de 5000 nodos: el bbox se interpretó mal. Para y avísame.

---

### FASE C — A* propio (`ai/nav/astar.py`)

Este es el algoritmo de navegación que presentamos como nuestro. Usa
`networkx.astar_path`, pero la heurística la escribes tú y es donde está todo el riesgo.

```python
def heuristica_tiempo(G, v_max_ms):
    """Devuelve una función h(n, meta) = haversine_metros(n, meta) / v_max_ms,
    en SEGUNDOS."""
```

> **El error que rompe esto:** el peso es `travel_time`, que está en segundos. Si tu
> heurística devuelve metros, sobreestima por un factor de ~10 y A* deja de ser óptimo
> (NetworkX lo advierte explícitamente en su documentación: heurística inadmisible →
> el resultado puede no ser el camino más corto). Divide entre la velocidad **máxima**
> del grafo, nunca la promedio — con la promedio también sobreestimas.

Los nodos de OSMnx traen `x` = longitud, `y` = latitud.

```python
def ruta_astar(G, nodo_origen, nodo_destino, v_max_ms) -> dict | None:
    """
    nx.astar_path(G, o, d, heuristic=..., weight='travel_time')
    Devuelve:
      {"segundos": float, "metros": float,
       "polilinea": [[lon, lat], ...],   # orden GeoJSON, listo para MapLibre
       "nodos": int}
    Suma 'travel_time' y 'length' arista por arista sobre el camino devuelto.
    None si no hay camino.
    """
```

El grafo es un **multigrafo**: puede haber varias aristas entre el mismo par de nodos.
Al acumular, toma siempre la de menor `travel_time`.

Escribe `ai/nav/test_astar.py` con tres pruebas, sobre 5 pares de nodos aleatorios:
1. El camino es conexo — cada par consecutivo es una arista real del grafo.
2. `segundos` coincide con `nx.shortest_path_length(G, o, d, weight='travel_time')`
   dentro de 0.1%.
3. La polilínea tiene al menos tantos puntos como nodos el camino.

> ### 🚦 COMPUERTA C
> ```powershell
> python -m pytest ai/nav/test_astar.py -v
> ```
> **Si la prueba 2 falla, la heurística no es admisible. PARA y avísame** — no la
> "ajustes" con un factor hasta que pase. Un A* con heurística mala da rutas que se
> ven plausibles pero no son óptimas, y eso es justo lo que no podemos presentar.

---

### FASE D — Proyección y geometría (`ai/vygo/geo_mty.py` + `ai/scripts/build_nav.py`)

**`ai/vygo/geo_mty.py`** — módulo nuevo y aislado. No importa nada de `geo.py` ni lo
modifica. Solo proyecta rejilla → coordenadas reales.

```python
def celda_a_latlon(x: float, y: float, escala_km_por_celda: float) -> tuple[float, float]
```

Transformación afín calibrada: **una celda debe medir en el mapa los mismos km que el
generador asumió.** Ancla el origen de la rejilla en la esquina SW del bbox. Usa
1° lat = 110.574 km, 1° lon = 111.320·cos(lat) km.

Si la rejilla proyectada excede el bbox, **no la recortes**: expande el bbox
simétricamente, vuelve a la Fase B para rebajar el grafo, y dime cuántos grados creció.

Incluye un `assert`: la distancia haversine entre dos celdas adyacentes proyectadas
coincide con `escala_km_por_celda` dentro de 2%.

**`ai/scripts/build_nav.py`:**

1. Lee `ai/demo/replay.json` y `cargar_grafo()`.
2. Proyecta cada parada con `celda_a_latlon`.
3. Pega cada coordenada a la red vial:
   `ox.distance.nearest_nodes(G, X=lons, Y=lats, return_dist=True)`
   **Pasa todas las coordenadas en una sola llamada** — usa el índice espacial y es
   órdenes de magnitud más rápido que una por una.
   Si alguna queda a más de 300 m del nodo más cercano, repórtala: la proyección la
   mandó fuera de la traza vial.
4. Para cada par de paradas **consecutivas** de cada replay, corre `ruta_astar`.
   Cachea por `(nodo_origen, nodo_destino)` — los pares se repiten.
5. Escribe `ai/demo/geometria.json`:

```json
{
  "meta": {"nodos_grafo": N, "aristas": M, "v_max_ms": X,
           "pares_totales": P, "pares_resueltos": R, "ms_por_consulta": T},
  "paradas_snap": {"serial": [[lon,lat],...], "vygo": [[lon,lat],...]},
  "tramos": {
    "serial": [{"de":0,"a":1,"segundos":..,"metros":..,"polilinea":[[lon,lat],..]}, ...],
    "vygo":   [...]
  },
  "totales": {"serial": {"km": X, "min": Y}, "vygo": {"km": X, "min": Y}}
}
```

Donde A* no resuelva, `"polilinea": null` — el HTML dibujará recta punteada ahí.

6. Imprime, y guarda en `ai/reports/DEMO.md`:
   - km reales totales por política
   - **km reales por entrega** por política ← este es el número de gasolina del pitch
   - pares no resueltos
   - ms promedio por consulta A*

> ### 🚦 COMPUERTA D
> **Si más del 10% de los pares no se resuelve, para y avísame.** Probablemente el
> bbox corta calles por las que pasan las rutas.

---

### FASE E — Visualizador (`ai/demo/turno.html`)

**Un solo archivo.** MapLibre GL JS desde CDN (`cdnjs`), estilo MapTiler `dataviz`.

**API key:** búscala en la config del frontend (`.env`, `.env.local`, donde esté
`VITE_MAPTILER_KEY`) e incrústala como constante. Si no la encuentras, deja
`const MAPTILER_KEY = "PEGAR_AQUI";` y dímelo en el reporte.

**`replay.json` y `geometria.json` van EMBEBIDOS como objetos JS dentro del HTML**, no
por `fetch` — el protocolo `file://` bloquea fetch local y la demo tiene que abrir con
doble clic. El archivo es autocontenido salvo por los tiles.

Elementos:

- Dos mapas MapLibre lado a lado, mismo centro y zoom, **sincronizados** (mover uno
  mueve el otro).
- Marcadores: círculo **verde lima** = recoger, círculo **azul marino** = entregar, con
  el número de orden dentro. El repartidor es un marcador que se interpola linealmente
  a lo largo de la polilínea.
- Trayecto recorrido en sólido; pendiente en semitransparente.
- Contador de **ganancia en MXN** arriba de cada mapa, incrementando al completar cada
  entrega.
- Contador de **km reales acumulados** por política.
- Barras de frescura por pedido activo (θ = 25 min), en rojo bajo 5 min restantes.
- Panel inferior de decisión: en el minuto de cada decisión registrada, muestra `Δf`,
  `Δt`, `ratio` contra `ρ*`, y el veredicto ACEPTA/RECHAZA con una frase en español:
  *"gana $X por minuto extra; el umbral es $Y"*.
- Banner de **surge al minuto 60**.
- Controles: play/pausa, 1× / 4× / 16×, barra de tiempo arrastrable, reinicio.
- Al pie, letra chica:
  > *"Navegación por A* sobre el grafo vial de OpenStreetMap (Monterrey), heurística
  > haversine/v_max. Secuencia de paradas decidida por el agente VYGO."*

**Modo degradado — obligatorio, no opcional.** Si los tiles de MapTiler no cargan en
4 segundos (sin internet en el venue, key inválida, MapTiler caído), oculta los mapas y
renderiza el mismo replay en un `<canvas>` de rejilla abstracta, con el mismo reloj y
los mismos paneles. **La demo nunca debe quedar en pantalla blanca.** Fuerza y prueba
este camino con el parámetro `?mapa=off`.

---

## 3. Verificación final

```powershell
python -m pytest ai/nav/test_astar.py -v
python ai/scripts/build_replay.py
python ai/scripts/build_nav.py
```

Luego, a ojo, abriendo `ai/demo/turno.html` por doble clic:

1. Ambos paneles corren con un solo reloj.
2. Los contadores terminan en **253.95** y **888.74**.
3. **Ninguna línea atraviesa una manzana, un camellón o el río.** Si ves una recta
   donde debería haber calle, ese par cayó a `null`: dime cuál.
4. El panel de decisión cambia de contenido a lo largo del turno.
5. `ai/demo/turno.html?mapa=off` corre el modo degradado.

---

## 4. Reporte

Escribe `ai/reports/DEMO.md` con:

- Cifras del replay vs `EVAL.md` (deben coincidir).
- Bbox final usado y si hubo que expandirlo.
- Nodos, aristas, MB del grafo; ms promedio por consulta A*.
- % de pares resueltos por A*.
- **km reales por entrega de cada política.**
- Tamaño del `turno.html` en KB.
- **Lista explícita de lo que NO funciona.** Sin adornos. Si algo quedó a medias, dilo.

Al final dame los comandos PowerShell exactos para regenerar todo desde cero, en orden.

---

## 5. Si algo se cae

No improvises arreglos que toquen código congelado. El orden de repliegue es:

| Falla | Repliegue |
|---|---|
| Overpass / OSMnx no instala | Sáltate A*: geometría en línea recta, el resto de la demo igual |
| A* no pasa la prueba de admisibilidad | Usa `nx.shortest_path` con `weight='travel_time'` y dilo en el reporte |
| MapTiler sin key o sin red | Modo `?mapa=off`, que ya construiste |
| El replay no reproduce EVAL.md | **Para todo.** Esto sí me lo tienes que reportar antes de seguir |
