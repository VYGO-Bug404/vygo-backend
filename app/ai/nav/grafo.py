"""
app.ai.nav.grafo
Grafo vial real de Monterrey (OSMnx / NetworkX) para navegación con A*.
Cubre Centro, Barrio Antiguo, Obispado y Mitras (BBOX_MTY).
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional, Any
import logging
import re

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
except ImportError:
    nx = None  # type: ignore

try:
    import osmnx as ox
    OSMNX_AVAILABLE = True
except ImportError:
    ox = None  # type: ignore
    OSMNX_AVAILABLE = False

try:
    from shapely import wkt as shapely_wkt
except ImportError:
    shapely_wkt = None


class LinestringGeom:
    """Clase liviana de geometría con propiedad .xy idéntica a Shapely LineString."""
    __slots__ = ("xy",)

    def __init__(self, pts: list[list[float]]):
        self.xy = ([p[0] for p in pts], [p[1] for p in pts])


def _cargar_graphml_directo(ruta: Path) -> Any:
    """Carga y procesa el GraphML de Monterrey usando NetworkX puro sin requerir bibliotecas C pesadas."""
    if nx is None:
        logger.warning("networkx no está instalado.")
        return None

    G = nx.read_graphml(ruta)

    # Convertir coordenadas de nodos a float
    for _n, d in G.nodes(data=True):
        if "x" in d:
            d["x"] = float(d["x"])
        if "y" in d:
            d["y"] = float(d["y"])

    # Convertir atributos de aristas a float y geometrías a objetos con .xy
    for _u, _v, _k, d in G.edges(keys=True, data=True):
        if "length" in d:
            d["length"] = float(d["length"])
        if "travel_time" in d:
            d["travel_time"] = float(d["travel_time"])
        if "speed_kph" in d:
            d["speed_kph"] = float(d["speed_kph"])

        geom_val = d.get("geometry")
        if isinstance(geom_val, str):
            if shapely_wkt is not None:
                try:
                    d["geometry"] = shapely_wkt.loads(geom_val)
                except Exception:
                    pass
            if isinstance(d.get("geometry"), str):
                raw_pts = re.findall(r"([-0-9.]+)\s+([-0-9.]+)", geom_val)
                if raw_pts:
                    pts = [[float(x), float(y)] for x, y in raw_pts]
                    d["geometry"] = LinestringGeom(pts)

    return G


def cargar_grafo() -> Any:
    """Si existe el cache lo carga; si no, intenta descargarlo con OSMnx."""
    if nx is None:
        logger.warning("networkx no está instalado. Use pip install networkx.")
        return None

    if RUTA_CACHE.exists():
        if OSMNX_AVAILABLE and ox is not None:
            try:
                return ox.io.load_graphml(RUTA_CACHE)
            except Exception as e:
                logger.info(f"Fallo carga con OSMnx ({e}), intentando NetworkX directo...")
        try:
            return _cargar_graphml_directo(RUTA_CACHE)
        except Exception as e:
            logger.warning(f"Error cargando cache {RUTA_CACHE} con NetworkX: {e}")

    if OSMNX_AVAILABLE and ox is not None:
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
        if nx is not None:
            largest_scc = max(nx.strongly_connected_components(G), key=len)
            return G.subgraph(largest_scc).copy()
        if OSMNX_AVAILABLE and ox is not None:
            return ox.truncate.largest_component(G, strongly=True)
    except Exception as e:
        logger.warning(f"Error obteniendo componente fuertemente conexa: {e}")
    return G
