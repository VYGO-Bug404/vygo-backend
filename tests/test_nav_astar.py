import pytest
from app.ai.nav.astar import (
    haversine_metros,
    heuristica_tiempo,
    ruta_vial_interpolada,
)
from app.ai.nav.geo_mty import sim2gps, gps2sim, BBOX_MTY
from app.core.schemas import MTY_MIN_LAT, MTY_MAX_LAT, MTY_MIN_LON, MTY_MAX_LON


def test_haversine_metros():
    # Macroplaza a Obispado en Monterrey (~4.2 km en línea recta)
    lat1, lon1 = 25.6690, -100.3090
    lat2, lon2 = 25.6740, -100.3510
    dist_m = haversine_metros(lon1, lat1, lon2, lat2)
    assert 4000 <= dist_m <= 4600


def test_ruta_vial_interpolada():
    # Macroplaza a San Pedro Garza García
    lon1, lat1 = -100.3094, 25.6714
    lon2, lat2 = -100.3590, 25.6550
    resultado = ruta_vial_interpolada(lon1, lat1, lon2, lat2, v_kmh=35.0)

    assert "segundos" in resultado
    assert "metros" in resultado
    assert "polilinea" in resultado
    assert resultado["segundos"] > 0
    assert resultado["metros"] > 0

    polilinea = resultado["polilinea"]
    assert len(polilinea) >= 3

    # Validar formato GeoJSON [lon, lat] y cotas de Monterrey
    for punto in polilinea:
        lon, lat = punto[0], punto[1]
        assert MTY_MIN_LON <= lon <= MTY_MAX_LON
        assert MTY_MIN_LAT <= lat <= MTY_MAX_LAT


def test_geo_mty_proyeccion():
    # Proyección desde el centro de la grilla (0.5, 0.5)
    lon, lat = sim2gps(0.5, 0.5)
    assert BBOX_MTY["min_lon"] <= lon <= BBOX_MTY["max_lon"]
    assert BBOX_MTY["min_lat"] <= lat <= BBOX_MTY["max_lat"]

    # Transformación inversa gps2sim
    gx, gy = gps2sim(lon, lat)
    assert abs(gx - 0.5) < 1e-4
    assert abs(gy - 0.5) < 1e-4
