"""FASE D (NIVEL-1-DEMO-MTY.md): proyección rejilla del simulador -> coordenadas reales
de Monterrey. Módulo NUEVO y AISLADO: no importa nada de `geo.py` ni lo modifica -- sólo
traduce (x, y) de la rejilla a (lat, lon) reales, ancladas sobre `nav.grafo.BBOX_MTY`
(sí se importa esa constante, para no duplicarla -- `nav.grafo` es un módulo nuevo de
esta misma tarea, no el `geo.py` original del simulador).

Convención de ejes: la rejilla original es abstracta (sin orientación geográfica
propia -- nunca la necesitó), así que la elección de qué eje es "norte" y cuál es
"este" es libre; aquí x crece hacia el ESTE y y crece hacia el NORTE desde la esquina
SW del bbox. Se documenta explícitamente para que sea auditable/corregible.

Transformación afín simple (no una proyección cartográfica real -- de sobra suficiente
para un grid de 10x10 km sobre un área de ~12x9.9 km): 1 grado de latitud = 110.574 km
(constante); 1 grado de longitud = 111.320*cos(lat) km (varía con la latitud -- se usa
la latitud fija de la esquina SW para todo el grid; el error de no recalcularla por
celda es despreciable en un área de este tamaño)."""

from __future__ import annotations

import math

from nav.grafo import BBOX_MTY

KM_POR_GRADO_LAT = 110.574
KM_POR_GRADO_LON_EN_ECUADOR = 111.320
_RADIO_TIERRA_KM = 6371.0

_LON_SW, _LAT_SW = BBOX_MTY[0], BBOX_MTY[1]  # (izq, abajo) de BBOX_MTY = esquina SW
_KM_POR_GRADO_LON = KM_POR_GRADO_LON_EN_ECUADOR * math.cos(math.radians(_LAT_SW))


def celda_a_latlon(x: float, y: float, escala_km_por_celda: float) -> tuple[float, float]:
    """(x, y) de la rejilla del simulador -> (lat, lon) reales. x crece al este, y crece
    al norte, ambos anclados en la esquina SW de `nav.grafo.BBOX_MTY`."""

    km_este = x * escala_km_por_celda
    km_norte = y * escala_km_por_celda
    lat = _LAT_SW + km_norte / KM_POR_GRADO_LAT
    lon = _LON_SW + km_este / _KM_POR_GRADO_LON
    return lat, lon


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _RADIO_TIERRA_KM * math.asin(math.sqrt(min(1.0, a)))


def _verificar_escala(escala_km_por_celda: float, tolerancia: float = 0.02) -> None:
    """La distancia haversine entre dos celdas adyacentes proyectadas debe coincidir con
    `escala_km_por_celda` dentro de `tolerancia` (2% por defecto), en ambos ejes."""

    lat0, lon0 = celda_a_latlon(0.0, 0.0, escala_km_por_celda)

    lat_este, lon_este = celda_a_latlon(1.0, 0.0, escala_km_por_celda)
    dist_este_km = _haversine_km(lat0, lon0, lat_este, lon_este)
    error_este = abs(dist_este_km - escala_km_por_celda) / escala_km_por_celda
    assert error_este <= tolerancia, (
        f"celda adyacente al este mide {dist_este_km:.4f} km, se esperaba "
        f"{escala_km_por_celda} km (+-{tolerancia * 100:.0f}%)"
    )

    lat_norte, lon_norte = celda_a_latlon(0.0, 1.0, escala_km_por_celda)
    dist_norte_km = _haversine_km(lat0, lon0, lat_norte, lon_norte)
    error_norte = abs(dist_norte_km - escala_km_por_celda) / escala_km_por_celda
    assert error_norte <= tolerancia, (
        f"celda adyacente al norte mide {dist_norte_km:.4f} km, se esperaba "
        f"{escala_km_por_celda} km (+-{tolerancia * 100:.0f}%)"
    )


# Se ejecuta al importar el módulo, con la escala real de este proyecto
# (`replay.json["meta"]["escala_km_por_celda"]` = 0.5, grid 20x20 = 10x10 km).
_verificar_escala(0.5)
