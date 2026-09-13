import math
from typing import Optional
from app.core.schemas import Punto

# Parámetros del modelo económico y de transporte para Monterrey
EARTH_RADIUS_KM = 6371.0
ROAD_TORTUOSITY_FACTOR = 1.28  # Factor de red vial real para Monterrey vs distancia geodésica
VELOCIDAD_MOTO_KMH = 28.0      # Velocidad media urbana en moto
TIEMPO_SERVICIO_RECOLECCION_MIN = 3.0  # Estacionar, esperar, verificar
TIEMPO_SERVICIO_ENTREGA_MIN = 2.0      # Llegar, timbre, entrega al cliente

# Parámetros de costo operativo (combustible, depreciación, datos móviles, tiempo)
COSTO_POR_KM_MXN = 2.50
COSTO_POR_MIN_MXN = 0.50

# Polígonos aproximados de zonas clave de Monterrey
ZONAS_MTY = {
    "centro": {"min_lat": 25.660, "max_lat": 25.690, "min_lon": -100.340, "max_lon": -100.290},
    "san_pedro": {"min_lat": 25.640, "max_lat": 25.675, "min_lon": -100.410, "max_lon": -100.340},
    "tec": {"min_lat": 25.635, "max_lat": 25.665, "min_lon": -100.310, "max_lon": -100.270},
    "cumbres": {"min_lat": 25.700, "max_lat": 25.750, "min_lon": -100.430, "max_lon": -100.360}
}

def haversine_km(p1: Punto, p2: Punto) -> float:
    """Calcula la distancia geodésica entre dos puntos en km."""
    lat1, lon1 = math.radians(p1.lat), math.radians(p1.lon)
    lat2, lon2 = math.radians(p2.lat), math.radians(p2.lon)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c

def distancia_vial_km(p1: Punto, p2: Punto) -> float:
    """Distancia estimada sobre la red vial de Monterrey."""
    return haversine_km(p1, p2) * ROAD_TORTUOSITY_FACTOR

def tiempo_viaje_min(distancia_km: float, clima: str = "normal", velocidad_kmh: float = VELOCIDAD_MOTO_KMH) -> float:
    """Tiempo de tránsito en minutos considerando clima."""
    mult_clima = 1.25 if clima == "lluvia" else 1.0
    if velocidad_kmh <= 0:
        velocidad_kmh = VELOCIDAD_MOTO_KMH
    return (distancia_km / velocidad_kmh) * 60.0 * mult_clima

def calcular_costo_marginal(delta_distancia_km: float, delta_tiempo_min: float) -> float:
    """Costo marginal = delta_km * c_km + delta_min * c_min."""
    return (delta_distancia_km * COSTO_POR_KM_MXN) + (delta_tiempo_min * COSTO_POR_MIN_MXN)

def calcular_tasa_marginal(ganancia_neta_mxn: float, delta_tiempo_min: float) -> float:
    """Tasa marginal en MXN/h = ganancia_neta / (delta_min / 60). Acotada a rango realista [0, 500]."""
    dt_horas = max(delta_tiempo_min, 4.0) / 60.0
    tasa = ganancia_neta_mxn / dt_horas
    return round(min(max(tasa, 0.0), 500.0), 1)

def clasificar_zona(p: Punto) -> str:
    """Identifica si un punto cae en una de las zonas gastronómicas principales."""
    for zona, b in ZONAS_MTY.items():
        if b["min_lat"] <= p.lat <= b["max_lat"] and b["min_lon"] <= p.lon <= b["max_lon"]:
            return zona
    return "periferia"

def es_zona_alta_demanda(p: Punto) -> bool:
    """True si el punto está en Centro, San Pedro o Tec."""
    return clasificar_zona(p) in {"centro", "san_pedro", "tec"}
