"""FASE D (NIVEL-1-DEMO-MTY.md).

D.2 -- proyecta el replay congelado (`demo/replay.json`) sobre el grafo vial RUTEABLE
de Monterrey (`nav.grafo.cargar_grafo_ruteable`, 14690 nodos -- nunca el grafo completo:
si una parada se pega a uno de los ~317 nodos fuera del mayor componente fuerte,
`ruta_astar` no encuentra camino de vuelta y devuelve `None`, no por un bug de A*).
Calcula las rutas A* reales entre paradas consecutivas y escribe `demo/geometria.json`.

D.3 -- reconstruye el trío de decisión (`delta_f`, `delta_min`, `delta_km`,
`tasa_marginal`, `rho_hat`, `holgura_frescura_min`, `frase`) para cada pedido ACEPTADO,
en frío, sobre el plan YA CONGELADO -- reusa el mismo grafo y el mismo cache de A* que
D.2 ya cargó, nunca vuelve a correr el entorno ni relee nada en vivo del simulador (ver
`reports/DEMO.md`, sección "Decisión de diseño", para por qué esto es seguro aquí y no
lo era dentro de `build_replay.py`). Actualiza IN PLACE el campo `"decisiones"` de
`demo/replay.json` -- todas las demás claves (`paradas`, `total_mxn`, `entregas`,
`pedidos`, `meta`) quedan BYTE A BYTE iguales.

`rho_hat` NO es la tasa realizada del turno completo (eso fue un error de la primera
versión de este script: con un solo valor constante para las 21 aceptaciones, la
PRIMERA entrega de vygo mostraba "te paga a $388/h, tu promedio hoy es $444/h" sobre una
ACEPTACIÓN -- inconsistente con la propia regla del modelo, que acepta cuando la tasa
marginal SUPERA el promedio). Se reconstruye en frío con `vygo.baselines.RhoHatMovil`
(la MISMA clase, misma ventana de 90 min, mismo valor inicial de 100 MXN/h que usa B2 en
vivo), alimentada cronológicamente con el ingreso neto (`pago_mxn - c_kappa*delta_km`)
de cada entrega, en el MISMO orden en que ocurrieron -- así `rho_hat` en la decisión de
un pedido es el promedio que el agente habría visto justo ANTES de esa entrega, no el
promedio final de todo el turno. Aproximación honesta, no exacta: al vivo `RhoHatMovil`
se alimenta en CADA paso de decisión (incluye el costo de tiempo entre entregas); aquí
sólo hay eventos de entrega en `replay.json`, así que el costo de tiempo entre entregas
no se descuenta -- el promedio reconstruido queda un poco más optimista que el real,
pero corrige la inconsistencia cualitativa (bajo al principio del turno, sube con las
entregas), que es lo que importa para el panel.

`c_kappa` = `vygo.env.COSTO_KM_MXN` (línea 56 de `env.py`: "c_kappa: combustible +
mantenimiento, aproximado" -- literalmente así etiquenada en el código, no un valor
inventado para esta tarea).

Los pedidos RECHAZADOS no se reconstruyen: no hay forma de saber qué otras ofertas
aparecieron en cada ronda perdida a partir del plan ya congelado. `decisiones` sólo
contiene aceptaciones -- exactamente tantas como `entregas` (Compuerta D2).

Uso: python ai/scripts/build_nav.py   (desde la raíz del repo)
     python scripts/build_nav.py      (desde ai/)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Callable, Optional

_AI_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))

import osmnx as ox  # noqa: E402

from nav.astar import ruta_astar  # noqa: E402
from nav.grafo import cargar_grafo_ruteable, velocidad_maxima_ms  # noqa: E402
from vygo.env import COSTO_KM_MXN  # noqa: E402
from vygo.geo_mty import celda_a_latlon  # noqa: E402

RUTA_REPLAY = _AI_ROOT / "demo" / "replay.json"
RUTA_GEOMETRIA = _AI_ROOT / "demo" / "geometria.json"
RUTA_DEMO_MD = _AI_ROOT / "reports" / "DEMO.md"

UMBRAL_SNAP_M = 300.0
UMBRAL_NO_RESUELTOS = 0.10  # 10%, Compuerta D1

RutaCacheadaFn = Callable[[int, int], Optional[dict]]


def _proyectar(paradas: list[dict], escala: float) -> list[tuple[float, float]]:
    return [celda_a_latlon(p["celda_x"], p["celda_y"], escala) for p in paradas]


def _tramos_de(nodos_pol: list[int], ruta_cacheada: RutaCacheadaFn) -> list[dict]:
    tramos = []
    for i in range(len(nodos_pol) - 1):
        o, d = nodos_pol[i], nodos_pol[i + 1]
        resultado = ruta_cacheada(o, d)
        if resultado is None:
            tramos.append({"de": i, "a": i + 1, "segundos": None, "metros": None, "polilinea": None})
        else:
            tramos.append({
                "de": i, "a": i + 1, "segundos": resultado["segundos"], "metros": resultado["metros"],
                "polilinea": resultado["polilinea"],
            })
    return tramos


def _totales_de(tramos: list[dict]) -> dict:
    segs = [t["segundos"] for t in tramos if t["segundos"] is not None]
    mets = [t["metros"] for t in tramos if t["metros"] is not None]
    return {"km": sum(mets) / 1000.0, "min": sum(segs) / 60.0}


def _tiempo_km_secuencia(nodos_pol: list[int], ruta_cacheada: RutaCacheadaFn) -> Optional[tuple[float, float]]:
    """Minutos y km totales de A* sobre una secuencia de nodos YA SNAPEADOS, sumando
    tramo a tramo consecutivo. `None` si algún tramo no tiene camino."""

    if len(nodos_pol) < 2:
        return 0.0, 0.0
    total_s = 0.0
    total_m = 0.0
    for i in range(len(nodos_pol) - 1):
        resultado = ruta_cacheada(nodos_pol[i], nodos_pol[i + 1])
        if resultado is None:
            return None
        total_s += resultado["segundos"]
        total_m += resultado["metros"]
    return total_s / 60.0, total_m / 1000.0


def _reconstruir_decisiones(
    paradas: list[dict], nodos_pol: list[int], total_mxn: float, duracion_min: float,
    ruta_cacheada: RutaCacheadaFn,
) -> tuple[list[dict], list[dict]]:
    """Devuelve (decisiones, anomalias). `anomalias`: pedidos con delta_min<=0 o
    tasa_marginal<0 -- Compuerta D2 los reporta y detiene la escritura, no se filtran
    silenciosamente."""

    rho_hat = total_mxn / (duracion_min / 60.0)

    resultado_completo = _tiempo_km_secuencia(nodos_pol, ruta_cacheada)
    if resultado_completo is None:
        raise RuntimeError("la secuencia completa no es ruteable -- no debería pasar en el componente fuerte")
    min_completo, km_completo = resultado_completo

    indice_p: dict[str, int] = {}
    indice_d: dict[str, int] = {}
    for i, p in enumerate(paradas):
        (indice_p if p["tipo"] == "P" else indice_d)[p["pedido_id"]] = i

    decisiones: list[dict] = []
    anomalias: list[dict] = []

    for pedido_id, i_p in indice_p.items():
        if pedido_id not in indice_d:
            continue  # recogido pero no entregado dentro de la ventana del turno

        i_d = indice_d[pedido_id]
        indices_excluir = {i_p, i_d}
        nodos_reducidos = [n for j, n in enumerate(nodos_pol) if j not in indices_excluir]

        resultado_reducido = _tiempo_km_secuencia(nodos_reducidos, ruta_cacheada)
        if resultado_reducido is None:
            raise RuntimeError(f"secuencia sin {pedido_id} no es ruteable")
        min_reducido, km_reducido = resultado_reducido

        delta_min = min_completo - min_reducido
        delta_km = km_completo - km_reducido
        delta_f = paradas[i_d]["pago_mxn"]
        holgura_frescura_min = paradas[i_d]["frescura_restante_min"]

        if delta_min <= 0:
            anomalias.append({"pedido_id": pedido_id, "motivo": "delta_min<=0", "delta_min": delta_min})
            continue

        tasa_marginal = (delta_f - COSTO_KM_MXN * delta_km) / delta_min * 60.0
        if tasa_marginal < 0:
            anomalias.append({
                "pedido_id": pedido_id, "motivo": "tasa_marginal<0",
                "tasa_marginal": tasa_marginal, "delta_f": delta_f, "delta_km": delta_km, "delta_min": delta_min,
            })
            continue

        decisiones.append({
            "oferta_id": pedido_id,
            "accion": "aceptado",
            "tasa_marginal": round(tasa_marginal, 1),
            "rho_hat": round(rho_hat, 1),
            "delta_min": round(delta_min, 1),
            "delta_km": round(delta_km, 2),
            "holgura_frescura_min": round(holgura_frescura_min, 1) if holgura_frescura_min is not None else None,
            "frase": f"Aceptado: te paga a ${tasa_marginal:.0f}/h, tu promedio hoy es ${rho_hat:.0f}/h.",
        })

    return decisiones, anomalias


def main() -> None:
    datos = json.loads(RUTA_REPLAY.read_text(encoding="utf-8"))
    escala = datos["meta"]["escala_km_por_celda"]
    duracion_min = datos["meta"]["duracion_min"]

    G = cargar_grafo_ruteable()
    v_max_ms = velocidad_maxima_ms(G)

    paradas_serial = datos["serial"]["paradas"]
    paradas_vygo = datos["vygo"]["paradas"]

    latlon_serial = _proyectar(paradas_serial, escala)
    latlon_vygo = _proyectar(paradas_vygo, escala)

    # Snap en UNA sola llamada para TODAS las coordenadas -- usa el índice espacial.
    todos_latlon = latlon_serial + latlon_vygo
    lats = [ll[0] for ll in todos_latlon]
    lons = [ll[1] for ll in todos_latlon]
    nodos_arr, dists_arr = ox.distance.nearest_nodes(G, X=lons, Y=lats, return_dist=True)
    nodos = [int(n) for n in nodos_arr]
    dists = [float(d) for d in dists_arr]

    n_serial = len(latlon_serial)
    nodos_serial, dists_serial = nodos[:n_serial], dists[:n_serial]
    nodos_vygo, dists_vygo = nodos[n_serial:], dists[n_serial:]

    lejanas = [(i, d) for i, d in enumerate(dists_serial + dists_vygo) if d > UMBRAL_SNAP_M]
    if lejanas:
        print(f"AVISO: {len(lejanas)} paradas a más de {UMBRAL_SNAP_M:.0f} m de su nodo más cercano:")
        for i, d in lejanas:
            print(f"  índice {i}: {d:.1f} m")
    else:
        print(f"snap OK: las {len(dists)} paradas quedaron a menos de {UMBRAL_SNAP_M:.0f} m de su nodo (máx observado: {max(dists):.1f} m)")

    cache_astar: dict[tuple[int, int], Optional[dict]] = {}
    tiempos_consulta_s: list[float] = []

    def _ruta_cacheada(o: int, d: int) -> Optional[dict]:
        clave = (o, d)
        if clave not in cache_astar:
            t0 = time.perf_counter()
            cache_astar[clave] = ruta_astar(G, o, d, v_max_ms)
            tiempos_consulta_s.append(time.perf_counter() - t0)
        return cache_astar[clave]

    # --- D.2: geometria.json ---
    tramos_serial = _tramos_de(nodos_serial, _ruta_cacheada)
    tramos_vygo = _tramos_de(nodos_vygo, _ruta_cacheada)

    pares_totales = len(tramos_serial) + len(tramos_vygo)
    pares_resueltos = sum(1 for t in tramos_serial + tramos_vygo if t["polilinea"] is not None)
    pct_no_resueltos = 1.0 - (pares_resueltos / pares_totales if pares_totales else 1.0)

    totales_serial = _totales_de(tramos_serial)
    totales_vygo = _totales_de(tramos_vygo)
    ms_por_consulta = (sum(tiempos_consulta_s) / len(tiempos_consulta_s) * 1000.0) if tiempos_consulta_s else 0.0

    geometria = {
        "meta": {
            "nodos_grafo": G.number_of_nodes(), "aristas": G.number_of_edges(), "v_max_ms": v_max_ms,
            "pares_totales": pares_totales, "pares_resueltos": pares_resueltos, "ms_por_consulta": ms_por_consulta,
        },
        "paradas_snap": {
            "serial": [[lon, lat] for lat, lon in latlon_serial],
            "vygo": [[lon, lat] for lat, lon in latlon_vygo],
        },
        "tramos": {"serial": tramos_serial, "vygo": tramos_vygo},
        "totales": {"serial": totales_serial, "vygo": totales_vygo},
    }
    RUTA_GEOMETRIA.write_text(json.dumps(geometria, ensure_ascii=False), encoding="utf-8")

    print(f"\npares_totales={pares_totales}  pares_resueltos={pares_resueltos}  ({pct_no_resueltos * 100:.1f}% no resueltos)")
    print(f"ms_por_consulta={ms_por_consulta:.2f}")
    print(f"serial: {totales_serial['km']:.2f} km, {totales_serial['min']:.1f} min")
    print(f"vygo:   {totales_vygo['km']:.2f} km, {totales_vygo['min']:.1f} min")

    if pct_no_resueltos > UMBRAL_NO_RESUELTOS:
        print(f"\nCOMPUERTA D1: FALLA -- {pct_no_resueltos * 100:.1f}% de pares sin resolver (> 10%). Deteniendo.")
        sys.exit(1)
    print(f"\nCOMPUERTA D1: PASA ({pct_no_resueltos * 100:.1f}% <= 10%)")

    km_por_entrega_serial = totales_serial["km"] / datos["serial"]["entregas"]
    km_por_entrega_vygo = totales_vygo["km"] / datos["vygo"]["entregas"]
    print(f"km por entrega -- serial: {km_por_entrega_serial:.2f}  vygo: {km_por_entrega_vygo:.2f}")

    # --- D.3: decisiones reconstruidas, en frío ---
    decisiones_serial, anomalias_serial = _reconstruir_decisiones(
        paradas_serial, nodos_serial, datos["serial"]["total_mxn"], duracion_min, _ruta_cacheada,
    )
    decisiones_vygo, anomalias_vygo = _reconstruir_decisiones(
        paradas_vygo, nodos_vygo, datos["vygo"]["total_mxn"], duracion_min, _ruta_cacheada,
    )

    anomalias = [{"politica": "serial", **a} for a in anomalias_serial] + [{"politica": "vygo", **a} for a in anomalias_vygo]
    if anomalias:
        print("\nCOMPUERTA D2: FALLA -- anomalías encontradas, no se escribe replay.json:")
        for a in anomalias:
            print(f"  {a}")
        sys.exit(1)

    if len(decisiones_serial) != datos["serial"]["entregas"] or len(decisiones_vygo) != datos["vygo"]["entregas"]:
        print(
            f"\nCOMPUERTA D2: FALLA -- decisiones(serial)={len(decisiones_serial)} vs "
            f"entregas={datos['serial']['entregas']}; decisiones(vygo)={len(decisiones_vygo)} vs "
            f"entregas={datos['vygo']['entregas']}"
        )
        sys.exit(1)
    print(
        f"\nCOMPUERTA D2: PASA -- decisiones(serial)={len(decisiones_serial)}=entregas, "
        f"decisiones(vygo)={len(decisiones_vygo)}=entregas"
    )

    datos["serial"]["decisiones"] = decisiones_serial
    datos["vygo"]["decisiones"] = decisiones_vygo
    RUTA_REPLAY.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    print(f"\n{RUTA_REPLAY} actualizado (sólo 'decisiones'; paradas/total_mxn/entregas/pedidos/meta sin cambios)")

    print("\n-- decisiones serial --")
    for d in decisiones_serial:
        print(f"  {d['oferta_id']}: tasa_marginal={d['tasa_marginal']} MXN/h  {d['frase']}")
    print("-- decisiones vygo --")
    for d in decisiones_vygo:
        print(f"  {d['oferta_id']}: tasa_marginal={d['tasa_marginal']} MXN/h  {d['frase']}")


if __name__ == "__main__":
    main()
