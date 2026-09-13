"""
app.ai.nav.geo_mty
Proyección afín calibrada: Rejilla del simulador (x, y) -> Coordenadas reales de Monterrey (lat, lon).
Anclada en la esquina SW de BBOX_MTY.
"""

from __future__ import annotations
import math
from .grafo import BBOX_MTY as BBOX_MTY_TUPLE

BBOX_MTY = {
    "min_lon": BBOX_MTY_TUPLE[0],
    "min_lat": BBOX_MTY_TUPLE[1],
    "max_lon": BBOX_MTY_TUPLE[2],
    "max_lat": BBOX_MTY_TUPLE[3],
}

KM_POR_GRADO_LAT = 110.574
KM_POR_GRADO_LON_EN_ECUADOR = 111.320
_RADIO_TIERRA_KM = 6371.0

_LON_SW, _LAT_SW = BBOX_MTY["min_lon"], BBOX_MTY["min_lat"]  # Esquina SW de BBOX_MTY (-100.360, 25.630)
_KM_POR_GRADO_LON = KM_POR_GRADO_LON_EN_ECUADOR * math.cos(math.radians(_LAT_SW))


def celda_a_latlon(x: float, y: float, escala_km_por_celda: float = 0.5) -> tuple[float, float]:
    """
    (x, y) de la rejilla del simulador -> (lat, lon) reales de Monterrey.
    x crece al este, y crece al norte.
    """
    km_este = x * escala_km_por_celda
    km_norte = y * escala_km_por_celda
    lat = _LAT_SW + km_norte / KM_POR_GRADO_LAT
    lon = _LON_SW + km_este / _KM_POR_GRADO_LON
    return round(lat, 6), round(lon, 6)


def latlon_a_celda(lat: float, lon: float, escala_km_por_celda: float = 0.5) -> tuple[float, float]:
    """
    (lat, lon) reales de Monterrey -> (x, y) de la rejilla.
    """
    km_norte = (lat - _LAT_SW) * KM_POR_GRADO_LAT
    km_este = (lon - _LON_SW) * _KM_POR_GRADO_LON
    x = km_este / escala_km_por_celda
    y = km_norte / escala_km_por_celda
    return round(x, 2), round(y, 2)


def sim2gps(x: float, y: float, escala_km_por_celda: float = 0.5) -> tuple[float, float]:
    """Alias para interoperabilidad: retorna (lon, lat) en orden GeoJSON."""
    lat, lon = celda_a_latlon(x, y, escala_km_por_celda)
    return lon, lat


def gps2sim(lon: float, lat: float, escala_km_por_celda: float = 0.5) -> tuple[float, float]:
    """Alias para interoperabilidad: recibe (lon, lat) GeoJSON y retorna (x, y)."""
    return latlon_a_celda(lat, lon, escala_km_por_celda)

