# Evaluación pareada -- reto Infosys "The Courier"

**Medición oficial -- CPU sin contención, 2026-09-12**

Generado: 2026-09-12T22:40:19+00:00
Escenarios: 30 congelados en `scenarios/test_30.pkl` (ver `scenarios/test_30.sha256`), 15 con SURGE y 15 con CIERRE_VIAL, evento siempre a partir del minuto 60. Evaluación PAREADA: cada política corre EXACTAMENTE los mismos 30 escenarios.
Políticas evaluadas: B_SERIAL, B1, B2, agente(PPO)
B_SERIAL es el repartidor SIN VYGO hoy: una sola app, un pedido a la vez -- es la referencia real, no B1.

## Nota de reproducibilidad -- por qué estos números pueden variar entre corridas

Se detectó y confirmó en un bloque anterior: dos corridas completas de esta evaluación sobre los MISMOS 30 escenarios, con el MISMO código (verificado sin diferencias en env.py/generator.py/geo.py/sequencer.py/feasibility.py entre ambas), dieron rho_mediana de B1 = 213.19 MXN/h y, más tarde, 353.25 MXN/h. Causa aislada: `sequencer.held_karp` acota su enumeración exacta (<=3 pedidos, el caso típico) con un presupuesto de **reloj de pared** de 25 ms (`_LIMITE_TIEMPO_EXACTO_S`); si se agota, usa la mejor secuencia encontrada hasta ahí (siempre factible, nunca viola frescura) pero no necesariamente la óptima. Bajo contención de CPU -- como la que había mientras la otra sesión entrenaba PPO en el mismo equipo -- ese presupuesto se agota más seguido y la ruta elegida se degrada de forma no determinista.

No se corrigió: la corrección (p. ej. medir tiempo de CPU de proceso en vez de reloj de pared, o subir el límite) requiere tocar `sequencer.py`, fuera de alcance de esta tarea ("no toques el entorno").

**Esta corrida es la medición oficial**: PPO ya terminó de entrenar (descartado, ver sección de RL más abajo) y no había ningún otro proceso pesado corriendo en la máquina mientras se ejecutó (confirmado con `Get-Process python` antes de empezar) -- esta fuente de ruido no aplica a los números de este reporte.

## TOTAL

| Política | rho mediana | rho IQR | entregados | pedidos/h | tasa aceptación | puntualidad | km/pedido | bundling |
|---|---|---|---|---|---|---|---|---|
| B_SERIAL | 121.35 | [107.02, 140.52] | 5.63 | 2.82 | 0.00 | 1.00 | 6.53 | 0.51 |
| B1 | 350.51 | [311.86, 375.69] | 14.30 | 7.15 | 0.01 | 1.00 | 3.57 | 0.91 |
| B2 | 364.67 | [321.97, 384.89] | 14.80 | 7.40 | 0.00 | 1.00 | 3.42 | 0.91 |
| agente(PPO) | 349.38 | [317.04, 366.14] | 14.53 | 7.27 | 0.00 | 1.00 | 3.50 | 0.88 |

## ANTES del evento

| Política | rho mediana | rho IQR | entregados | pedidos/h | tasa aceptación | puntualidad | km/pedido | bundling |
|---|---|---|---|---|---|---|---|---|
| B_SERIAL | 119.68 | [91.05, 138.29] | 2.67 | 2.67 | 0.00 | 1.00 | 6.07 | 0.51 |
| B1 | 334.86 | [300.32, 344.18] | 6.90 | 6.90 | 0.01 | 1.00 | 3.60 | 0.94 |
| B2 | 337.07 | [300.72, 357.16] | 7.07 | 7.07 | 0.00 | 1.00 | 3.47 | 0.93 |
| agente(PPO) | 316.22 | [295.31, 369.00] | 7.13 | 7.13 | 0.00 | 1.00 | 3.44 | 0.92 |

## DESPUÉS del evento

| Política | rho mediana | rho IQR | entregados | pedidos/h | tasa aceptación | puntualidad | km/pedido | bundling |
|---|---|---|---|---|---|---|---|---|
| B_SERIAL | 130.86 | [111.94, 146.31] | 2.97 | 2.97 | 0.00 | 1.00 | 7.06 | 0.51 |
| B1 | 379.73 | [321.66, 428.46] | 7.40 | 7.40 | 0.01 | 0.97 | 3.41 | 0.89 |
| B2 | 386.64 | [331.90, 426.25] | 7.73 | 7.73 | 0.00 | 0.97 | 3.42 | 0.88 |
| agente(PPO) | 360.16 | [312.19, 413.39] | 7.40 | 7.40 | 0.00 | 1.00 | 3.74 | 0.82 |

## Estadística pareada (por escenario, no por medianas independientes)

Para cada par se calcula d_i = rho(a, escenario i) − rho(b, escenario i) en los 30 escenarios; se reporta la MEDIANA de esas diferencias con IC 95% por bootstrap (10000 remuestreos) sobre las diferencias mismas, y la tasa de victorias (en cuántos turnos rho_a > rho_b).

| Comparación | mediana(diferencia rho) | IC 95% | victorias |
|---|---|---|---|
| B2 vs B_SERIAL | +242.20 MXN/h | [+208.92, +255.12] | 30/30 |
| B2 vs B1 | +1.90 MXN/h | [-15.78, +23.64] | 15/30 |
| agente(PPO) vs B1 | -3.37 MXN/h | [-23.76, +18.05] | 13/30 |

## Turno de demo -- mayor ventaja de B2 sobre B_SERIAL

Escenario semilla=10000 (evento: surge), ventaja de B2 sobre B_SERIAL: **+311.99 MXN/h** de rho.

| | B2 | B_SERIAL |
|---|---|---|
| minutos | 120.0 | 120.0 |
| km | 53.00 | 44.00 |
| ingreso MXN | 888.74 | 253.95 |
| rho MXN/h | 412.57 | 100.58 |
| entregados | 16 | 5 |

Secuencia de paradas -- B2 (32 paradas):

```
  min    8.8  recogida     p12  (8, 8)
  min   13.3  entrega      p12  (11, 9)  +45.51 MXN
  min   17.1  recogida     p40  (12, 7)
  min   21.3  recogida     p17  (8, 7)
  min   23.3  entrega      p17  (6, 7)  +49.01 MXN
  min   25.5  recogida    p210  (8, 7)
  min   27.5  entrega      p40  (8, 9)  +70.63 MXN
  min   30.7  entrega     p210  (9, 11)  +53.44 MXN
  min   33.6  recogida   p2132  (9, 13)
  min   38.7  entrega    p2132  (7, 16)  +60.85 MXN
  min   44.2  recogida   p2801  (9, 13)
  min   44.2  recogida   p2135  (9, 13)
  min   49.5  entrega    p2801  (9, 8)  +62.97 MXN
  min   51.5  entrega    p2135  (11, 8)  +51.48 MXN
  min   53.6  recogida   p2800  (12, 7)
  min   58.6  entrega    p2800  (14, 10)  +54.94 MXN
  min   62.6  recogida   p4036  (12, 12)
  min   64.7  recogida   p4508  (12, 14)
  min   67.9  entrega    p4036  (12, 17)  +52.56 MXN
  min   74.2  entrega    p4508  (11, 12)  +47.59 MXN
  min   78.1  recogida   p5340  (12, 15)
  min   79.1  entrega    p5340  (12, 14)  +41.30 MXN
  min   81.1  recogida   p5733  (12, 12)
  min   87.8  entrega    p5733  (8, 10)  +73.14 MXN
  min   91.1  recogida   p6250  (8, 7)
  min   96.5  entrega    p6250  (4, 6)  +73.98 MXN
  min  103.1  recogida   p8183  (8, 8)
  min  109.8  entrega    p8183  (11, 5)  +70.52 MXN
  min  112.8  recogida   p9059  (9, 5)
  min  112.8  recogida   p9058  (9, 5)
  min  117.1  entrega    p9059  (10, 8)  +43.49 MXN
  min  119.1  entrega    p9058  (11, 7)  +37.34 MXN
```

Secuencia de paradas -- B_SERIAL (10 paradas):

```
  min    8.8  recogida     p12  (8, 8)
  min   13.3  entrega      p12  (11, 9)  +45.51 MXN
  min   32.0  recogida   p1242  (5, 12)
  min   36.2  entrega    p1242  (8, 11)  +46.42 MXN
  min   58.3  recogida   p3311  (0, 3)
  min   64.5  entrega    p3311  (5, 2)  +62.80 MXN
  min   81.4  recogida   p5911  (6, 16)
  min   84.7  entrega    p5911  (3, 16)  +45.56 MXN
  min  107.5  recogida   p7894  (16, 7)
  min  112.7  entrega    p7894  (14, 4)  +53.66 MXN
```

## Reacción al evento -- ejemplo concreto (emergente, no programado)

### SURGE

SURGE en (0,4), x1.4 tarifa / x1.6 intensidad de llegada, minuto 60-105. Misma oferta (recoger en (0,4), entregar en (0,10), 596s de viaje), misma `politica_umbral`, mismo `rho_hat`=150 MXN/h:  
  - Antes del surge: precio=22.36 MXN -> tasa_marginal=98.8 MXN/h < rho_hat -> decisión = rechazar_todas.  
  - Con el surge activo: precio=31.30 MXN (x1.4) -> tasa_marginal=152.8 MXN/h > rho_hat -> decisión = aceptar oferta 0.  
  Nada en `politica_umbral` sabe que existe un evento: sólo ve un precio más alto y la MISMA regla de umbral cruza de rechazar a aceptar.

### CIERRE_VIAL

CIERRE_VIAL en la columna 10 (factor_detour=1.7x), minuto 60-100. Mismos 4 stops (A y B, recogida/entrega a los dos lados de la columna 10), mismo `held_karp`:  
  - Antes del cierre: tiempo_total=1423s, dist_total=12000m, orden=[0, 2, 1, 3].  
  - Con el cierre activo: tiempo_total=1828s (+405s, +28%), dist_total=15500m, orden=[0, 2, 1, 3].  
  `held_karp` no sabe que hay un evento: sólo ve un `travel_fn` que ahora cobra 1.7x al cruzar la columna 10, y recalcula el óptimo con esa única diferencia.

## Experimento de RL -- honesto

**BC (behavioral cloning) sobre B2**: 10 épocas, 40 000 transiciones de entrenamiento / 10 000 de validación. Concordancia final con B2 en validación **99.8%** (`reports/bc_curva.json`, época 10: `concordancia_val=0.9985`). El clon aprende la regla de umbral casi a la perfección como problema de clasificación -- el cuello de botella de PPO no es que no pueda imitar a B2.

**PPO desde ese checkpoint**: `MaskablePPO` inicializado con los pesos de `bc_policy.pt` (no entrenado desde cero), afinado on-policy encima. Resultado en este holdout de 30 escenarios: **agente(PPO) vs B1**: mediana(diferencia de rho)=-3.37 MXN/h, gana en 13/30 turnos frente a B1 -- **PPO descartado**, no supera al baseline simple en este holdout.

**Evidencia de que la política casi no se movió durante el afinado on-policy**: `approx_kl` en `reports/train_ppo.log` se mantiene del orden de 1e-9 a 1e-5 (varias filas en exactamente 0.0) a lo largo del entrenamiento -- PPO está ajustando casi nada respecto al punto de partida heredado de BC, no está descubriendo una política distinta.

**Diagnóstico**: el entorno está saturado por el tope duro `K_A_MAXIMO=4` -- instrumentado con `feasibility.CONTADOR_MOTIVOS` en el bloque anterior, el motivo `tope_ka` explica el **89.1%** del histograma de rechazos (`reports/HANDOFF.md`). Con el plan lleno casi todo el turno, aceptar todo lo factible ya es casi óptimo: no queda margen de SELECCIÓN entre ofertas que una política de RL pueda aprender a explotar. La ganancia real de este sistema está en AGRUPAR pedidos (B1/B2 vs B_SERIAL, ver tabla y turno de demo arriba), no en escoger mejor entre ofertas visibles (B2 vs B1, y por lo mismo PPO vs B1) -- ahí el margen ya está casi agotado por el tope de capacidad, no por falta de entrenamiento.
