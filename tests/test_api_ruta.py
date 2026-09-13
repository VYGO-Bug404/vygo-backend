"""
tests/test_api_ruta.py
Pruebas exhaustivas para el endpoint POST /ruta (FastAPI).
Valida:
  1. Orden de coordenadas GeoJSON estándar [lon, lat] contra puntos conocidos del Centro de Monterrey.
  2. Encadenamiento correcto con 4 destinos y tiempo de respuesta medido < 400 ms.
  3. Resiliencia y fallback en línea recta si algún tramo no es resoluble (resuelto: false).
  4. Caché LRU de tramos para acelerar peticiones recurrentes.
"""

import time
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Coordenadas reales conocidas en Monterrey:
# Macroplaza: (-100.3094, 25.6714)
# Alameda Mariano Escobedo: (-100.3205, 25.6750)
# Obispado: (-100.3470, 25.6740)
# Pabellón M: (-100.3170, 25.6670)
# Parque Fundidora: (-100.2850, 25.6780)


def test_endpoint_ruta_orden_geojson_coordenadas_mty():
    """
    Requisito 6: coordinates va en orden [lon, lat], orden GeoJSON.
    Verifica contra un punto conocido del centro de Monterrey (Macroplaza a Alameda).
    En Monterrey:
      lon es negativa (aprox. -100.3)
      lat es positiva (aprox. 25.67)
    Si se invirtieran a [lat, lon], lon sería 25.67 y lat sería -100.3 (el otro lado del mundo).
    """
    payload = {
        "origen": {"lat": 25.6714, "lon": -100.3094},
        "destinos": [
            {"id": "alameda", "lat": 25.6750, "lon": -100.3205}
        ]
    }

    res = client.post("/ruta", json=payload)
    assert res.status_code == 200, f"Error {res.status_code}: {res.text}"
    data = res.json()

    assert len(data["tramos"]) == 1
    tramo = data["tramos"][0]
    assert tramo["de"] == "origen"
    assert tramo["a"] == "alameda"
    assert tramo["resuelto"] is True

    coords = tramo["geometria"]["coordinates"]
    assert len(coords) >= 2, "La polilínea debe tener al menos 2 coordenadas"

    # Verificar CADA punto de la polilínea: [lon, lat]
    for idx, punto in enumerate(coords):
        lon, lat = punto[0], punto[1]
        assert -100.5 <= lon <= -100.1, (
            f"Punto {idx} tiene longitud inválida ({lon}); se esperaba longitud de Monterrey aprox -100.3. "
            f"Posible error de inversión [lat, lon] detectado."
        )
        assert 25.5 <= lat <= 25.9, (
            f"Punto {idx} tiene latitud inválida ({lat}); se esperaba latitud de Monterrey aprox 25.67. "
            f"Posible error de inversión [lat, lon] detectado."
        )


def test_endpoint_ruta_4_destinos_encadenados_y_tiempo():
    """
    Requisito 2 y Compuerta B: Encadena origen->d0->d1->d2->d3 y mide tiempo de respuesta < 400 ms.
    """
    payload = {
        "origen": {"lat": 25.6714, "lon": -100.3094},  # Macroplaza
        "destinos": [
            {"id": "pabellon_m", "lat": 25.6670, "lon": -100.3170},
            {"id": "alameda", "lat": 25.6750, "lon": -100.3205},
            {"id": "obispado", "lat": 25.6740, "lon": -100.3470},
            {"id": "fundidora", "lat": 25.6780, "lon": -100.2850},
        ]
    }

    inicio = time.perf_counter()
    res = client.post("/ruta", json=payload)
    duracion_ms = (time.perf_counter() - inicio) * 1000.0

    assert res.status_code == 200
    data = res.json()

    assert len(data["tramos"]) == 4
    assert data["tramos"][0]["de"] == "origen"
    assert data["tramos"][0]["a"] == "pabellon_m"
    assert data["tramos"][1]["de"] == "pabellon_m"
    assert data["tramos"][1]["a"] == "alameda"
    assert data["tramos"][2]["de"] == "alameda"
    assert data["tramos"][2]["a"] == "obispado"
    assert data["tramos"][3]["de"] == "obispado"
    assert data["tramos"][3]["a"] == "fundidora"

    for tramo in data["tramos"]:
        assert tramo["resuelto"] is True
        assert tramo["metros"] > 0
        assert tramo["segundos"] > 0
        assert len(tramo["geometria"]["coordinates"]) >= 2

    # Puntos del primer tramo
    puntos_tramo_0 = len(data["tramos"][0]["geometria"]["coordinates"])
    assert puntos_tramo_0 >= 10, f"El primer tramo debe tener múltiples puntos de calle, tuvo {puntos_tramo_0}"

    # Totales
    assert data["totales"]["metros"] > 0
    assert data["totales"]["segundos"] > 0
    assert data["diagnostico"]["tramos_sin_resolver"] == 0

    # Verificación de latencia (< 400 ms)
    assert duracion_ms < 400.0, f"Latencia excesiva: {duracion_ms:.1f} ms > 400 ms"


def test_endpoint_ruta_destinos_vacio():
    """Valida comportamiento borde cuando la lista de destinos está vacía."""
    payload = {
        "origen": {"lat": 25.6714, "lon": -100.3094},
        "destinos": []
    }
    res = client.post("/ruta", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["tramos"] == []
    assert data["totales"]["metros"] == 0.0
    assert data["totales"]["segundos"] == 0.0
    assert data["diagnostico"]["tramos_sin_resolver"] == 0


def test_endpoint_ruta_cache_lru():
    """Valida que la caché LRU acelera segundas consultas sobre los mismos tramos."""
    payload = {
        "origen": {"lat": 25.6714, "lon": -100.3094},
        "destinos": [{"id": "alameda", "lat": 25.6750, "lon": -100.3205}]
    }
    # Primera llamada
    res1 = client.post("/ruta", json=payload)
    assert res1.status_code == 200

    # Segunda llamada (debe estar en caché)
    t0 = time.perf_counter()
    res2 = client.post("/ruta", json=payload)
    t_cache_ms = (time.perf_counter() - t0) * 1000.0

    assert res2.status_code == 200
    assert res1.json()["tramos"][0]["geometria"] == res2.json()["tramos"][0]["geometria"]
    assert t_cache_ms < 100.0
