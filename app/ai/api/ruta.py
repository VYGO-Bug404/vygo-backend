"""
ai.api.ruta / app.ai.api.ruta
Endpoint POST /ruta para cálculo encadenado de trayectorias de alta fidelidad con A*.
Devuelve la geometría vial exacta para cada salto entre el repartidor y los destinos solicitados.
"""

from __future__ import annotations
import time
import logging
from collections import OrderedDict
from threading import Lock
from typing import Optional, Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ai.nav.grafo import cargar_grafo_ruteable
from app.ai.nav.astar import ruta_astar, haversine_metros

logger = logging.getLogger("vygo.api.ruta")
router = APIRouter(tags=["Rutas"])

# 1. Carga del grafo ruteable fuertemente conexo UNA sola vez al iniciar el servidor (14,690 nodos)
_GRAFO = cargar_grafo_ruteable()
if _GRAFO is None:
    logger.error("No se pudo precalentar el grafo de Monterrey en POST /ruta")


# 4. Caché LRU en memoria acotada a 5,000 pares (nodo_origen, nodo_destino)
class LRUCacheRutas:
    def __init__(self, maxsize: int = 5000):
        self.maxsize = maxsize
        self._cache: OrderedDict[tuple[int, int], dict] = OrderedDict()
        self._lock = Lock()

    def get(self, key: tuple[int, int]) -> Optional[dict]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def set(self, key: tuple[int, int], val: dict) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = val
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


_CACHE_RUTAS = LRUCacheRutas(maxsize=5000)


# Modelos Pydantic estrictos
class Coordenada(BaseModel):
    lat: float = Field(..., description="Latitud (ej. 25.6690)")
    lon: float = Field(..., description="Longitud (ej. -100.3090)")


class DestinoRuta(BaseModel):
    id: str = Field(..., description="Identificador único del destino (ej. parada_1, pedido_c)")
    lat: float = Field(..., description="Latitud")
    lon: float = Field(..., description="Longitud")


class RutaRequest(BaseModel):
    origen: Coordenada = Field(..., description="Posición viva actual del repartidor (GPS)")
    destinos: list[DestinoRuta] = Field(
        default_factory=list,
        description="Lista ordenada de paradas a visitar",
    )


class GeometriaLineString(BaseModel):
    type: str = "LineString"
    coordinates: list[list[float]] = Field(
        ...,
        description="Coordenadas de la polilínea en orden estándar GeoJSON [[lon, lat], ...]",
    )


class TramoRuta(BaseModel):
    de: str = Field(..., description="ID del punto de partida del tramo")
    a: str = Field(..., description="ID del punto de llegada del tramo")
    segundos: float = Field(..., description="Tiempo estimado de tránsito en segundos")
    metros: float = Field(..., description="Distancia real del tramo en metros")
    geometria: GeometriaLineString = Field(..., description="Geometría GeoJSON LineString del tramo")
    resuelto: bool = Field(..., description="True si fue resuelto por A*, False si es fallback en línea recta")


class TotalesRuta(BaseModel):
    metros: float = Field(..., description="Suma total de metros recorridos")
    segundos: float = Field(..., description="Suma total de segundos de tránsito")


class DiagnosticoRuta(BaseModel):
    ms: float = Field(..., description="Tiempo total de cómputo en el servidor en milisegundos")
    tramos_sin_resolver: int = Field(..., description="Número de tramos donde A* no encontró conexión directa")


class RutaResponse(BaseModel):
    tramos: list[TramoRuta]
    totales: TotalesRuta
    diagnostico: DiagnosticoRuta


def _adherir_coordenadas_a_red(lons: list[float], lats: list[float]) -> list[int]:
    """
    3. Adhiere todas las coordenadas a la red vial en UNA sola llamada,
    aprovechando el índice espacial KD-Tree de OSMnx.
    """
    if _GRAFO is None or not lons:
        return []

    try:
        import osmnx as ox
        nodos = ox.distance.nearest_nodes(_GRAFO, X=lons, Y=lats)
        return [int(n) for n in nodos]
    except Exception as e:
        logger.warning(f"Fallback espacial cKDTree por error en nearest_nodes: {e}")
        from scipy.spatial import cKDTree
        nodos_g = list(_GRAFO.nodes)
        coords_g = [[_GRAFO.nodes[n]["x"], _GRAFO.nodes[n]["y"]] for n in nodos_g]
        tree = cKDTree(coords_g)
        puntos = list(zip(lons, lats))
        _, idxs = tree.query(puntos)
        return [int(nodos_g[i]) for i in idxs]


@router.post("/ruta", response_model=RutaResponse)
async def trazar_ruta(req: RutaRequest) -> RutaResponse:
    t_inicio = time.perf_counter()

    if not req.destinos:
        t_total_ms = round((time.perf_counter() - t_inicio) * 1000.0, 2)
        return RutaResponse(
            tramos=[],
            totales=TotalesRuta(metros=0.0, segundos=0.0),
            diagnostico=DiagnosticoRuta(ms=t_total_ms, tramos_sin_resolver=0),
        )

    # 2. Encadenar: origen -> d0, d0 -> d1, d1 -> d2...
    lons = [req.origen.lon] + [d.lon for d in req.destinos]
    lats = [req.origen.lat] + [d.lat for d in req.destinos]
    ids = ["origen"] + [d.id for d in req.destinos]

    # 3. Adhesión espacial en una sola llamada
    nodos = _adherir_coordenadas_a_red(lons, lats)

    tramos: list[TramoRuta] = []
    tramos_sin_resolver = 0

    for i in range(len(req.destinos)):
        id_de = ids[i]
        id_a = ids[i + 1]
        lon_de, lat_de = lons[i], lats[i]
        lon_a, lat_a = lons[i + 1], lats[i + 1]

        u = nodos[i] if i < len(nodos) else None
        v = nodos[i + 1] if (i + 1) < len(nodos) else None

        resultado_tramo: Optional[dict] = None

        if u is not None and v is not None and _GRAFO is not None:
            # 4. Consulta a la caché LRU (u, v)
            clave_cache = (u, v)
            resultado_tramo = _CACHE_RUTAS.get(clave_cache)

            if resultado_tramo is None:
                if u == v:
                    resultado_tramo = {
                        "segundos": 0.0,
                        "metros": 0.0,
                        "polilinea": [
                            [round(float(_GRAFO.nodes[u]["x"]), 6), round(float(_GRAFO.nodes[u]["y"]), 6)],
                            [round(float(_GRAFO.nodes[v]["x"]), 6), round(float(_GRAFO.nodes[v]["y"]), 6)],
                        ],
                        "nodos": 1,
                    }
                else:
                    resultado_tramo = ruta_astar(_GRAFO, u, v)

                if resultado_tramo is not None:
                    _CACHE_RUTAS.set(clave_cache, resultado_tramo)

        if resultado_tramo is not None and resultado_tramo.get("polilinea"):
            coords = resultado_tramo["polilinea"]
            # Garantizar que MapLibre reciba al menos 2 coordenadas para el LineString
            if len(coords) < 2:
                coords = [
                    [round(float(lon_de), 6), round(float(lat_de), 6)],
                    [round(float(lon_a), 6), round(float(lat_a), 6)],
                ]

            tramos.append(
                TramoRuta(
                    de=id_de,
                    a=id_a,
                    segundos=resultado_tramo["segundos"],
                    metros=resultado_tramo["metros"],
                    geometria=GeometriaLineString(coordinates=coords),
                    resuelto=True,
                )
            )
        else:
            # 5. Fallback en línea recta si A* devuelve None. NUNCA fallar la petición completa.
            tramos_sin_resolver += 1
            dist_m = round(haversine_metros(lon_de, lat_de, lon_a, lat_a), 2)
            segundos_est = round(dist_m / (25.0 / 3.6), 2)  # ~25 km/h
            coords_recta = [
                [round(float(lon_de), 6), round(float(lat_de), 6)],
                [round(float(lon_a), 6), round(float(lat_a), 6)],
            ]

            tramos.append(
                TramoRuta(
                    de=id_de,
                    a=id_a,
                    segundos=segundos_est,
                    metros=dist_m,
                    geometria=GeometriaLineString(coordinates=coords_recta),
                    resuelto=False,
                )
            )

    total_metros = round(sum(t.metros for t in tramos), 2)
    total_segundos = round(sum(t.segundos for t in tramos), 2)
    duracion_ms = round((time.perf_counter() - t_inicio) * 1000.0, 2)

    return RutaResponse(
        tramos=tramos,
        totales=TotalesRuta(metros=total_metros, segundos=total_segundos),
        diagnostico=DiagnosticoRuta(ms=duracion_ms, tramos_sin_resolver=tramos_sin_resolver),
    )
