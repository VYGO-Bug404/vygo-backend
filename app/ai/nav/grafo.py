"""
app.ai.nav.grafo
Grafo vial real de Monterrey (OSMnx) para navegación con A*.
Cubre Centro, Barrio Antiguo, Obispado y Mitras (BBOX_MTY).
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Any
import logging

logger = logging.getLogger("vygo.nav.grafo")

BBOX_MTY = (-100.360, 25.630, -100.240, 25.720)  # (izq, abajo, der, arriba) = (left, bottom, right, top)

_NAV_DIR = Path(__file__).resolve().parent
RUTA_CACHE = _NAV_DIR / "cache" / "mty_drive.graphml"

# Intentar habilitar truststore si existe (útil en entornos con proxy corporativo)
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

try:
    import networkx as nx
    import osmnx as ox
    OSMNX_AVAILABLE = True
except ImportError:
    nx = None  # type: ignore
    ox = None  # type: ignore
    OSMNX_AVAILABLE = False


def cargar_grafo() -> Any:
    """Si existe el cache lo carga; si no, intenta descargarlo con OSMnx."""
    if not OSMNX_AVAILABLE:
        logger.warning("osmnx no está instalado. Use pip install osmnx networkx.")
        return None

    if RUTA_CACHE.exists():
        try:
            return ox.io.load_graphml(RUTA_CACHE)
        except Exception as e:
            logger.warning(f"Error cargando cache {RUTA_CACHE}: {e}")

    try:
        G = ox.graph_from_bbox(BBOX_MTY, network_type="drive")
        G = ox.routing.add_edge_speeds(G)
        G = ox.routing.add_edge_travel_times(G)

        RUTA_CACHE.parent.mkdir(parents=True, exist_ok=True)
        ox.io.save_graphml(G, RUTA_CACHE)
        return G
    except Exception as e:
        logger.warning(f"No se pudo descargar grafo de Overpass OSMnx: {e}")
        return None


def velocidad_maxima_ms(G: Any) -> float:
    """Máximo de speed_kph sobre todas las aristas, convertido a m/s."""
    if G is None:
        return 25.0  # 90 km/h por defecto
    velocidades_kph = [datos["speed_kph"] for _u, _v, datos in G.edges(data=True) if "speed_kph" in datos]
    if not velocidades_kph:
        return 25.0
    return max(velocidades_kph) / 3.6


def cargar_grafo_ruteable() -> Any:
    """Grafo recortado al mayor componente fuertemente conexo para garantizar ruteabilidad de ida y vuelta."""
    G = cargar_grafo()
    if G is None:
        return None
    try:
        return ox.truncate.largest_component(G, strongly=True)
    except Exception as e:
        logger.warning(f"Error obteniendo componente fuertemente conexa: {e}")
        return G
