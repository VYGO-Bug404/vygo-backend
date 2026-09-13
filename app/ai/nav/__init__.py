"""
app.ai.nav
Módulo de navegación A* sobre el grafo vial real de Monterrey (OpenStreetMap).
"""

from .astar import ruta_astar, heuristica_tiempo
from .grafo import BBOX_MTY, cargar_grafo, cargar_grafo_ruteable, velocidad_maxima_ms

__all__ = [
    "BBOX_MTY",
    "cargar_grafo",
    "cargar_grafo_ruteable",
    "velocidad_maxima_ms",
    "ruta_astar",
    "heuristica_tiempo",
]
