"""Módulo geoespacial: Soporte dual para coordenadas GPS de Monterrey y rejilla GridWorld.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple, Optional

import numpy as np

from app.core.schemas import Punto
from app.core.metrics import (
    haversine_km,
    distancia_vial_km,
    tiempo_viaje_min,
    ROAD_TORTUOSITY_FACTOR,
    VELOCIDAD_MOTO_KMH,
)
from app.ai.schema import Clima, Vehiculo, VEHICULOS


def travel_fn_monterrey(
    pos1: Tuple[float, float] | Punto,
    pos2: Tuple[float, float] | Punto,
    t: float,
    clima: str = "normal",
    velocidad_kmh: float = VELOCIDAD_MOTO_KMH,
) -> Tuple[float, float]:
    """Retorna (tiempo_minutos, distancia_km) para viajar entre dos puntos GPS en Monterrey."""
    lat1 = pos1.lat if hasattr(pos1, "lat") else pos1[0]
    lon1 = pos1.lon if hasattr(pos1, "lon") else pos1[1]
    lat2 = pos2.lat if hasattr(pos2, "lat") else pos2[0]
    lon2 = pos2.lon if hasattr(pos2, "lon") else pos2[1]

    p1 = Punto(lat=lat1, lon=lon1)
    p2 = Punto(lat=lat2, lon=lon2)
    d_km = distancia_vial_km(p1, p2)
    t_min = tiempo_viaje_min(d_km, clima=clima, velocidad_kmh=velocidad_kmh)
    return t_min, d_km


@dataclass(frozen=True, slots=True)
class Corredor:
    eje: str  # "fila" | "columna"
    indice: int
    factor_detour: float = 1.7


def _cruza_corredor(origen: tuple[int, int], destino: tuple[int, int], corredor: Corredor) -> bool:
    k = 0 if corredor.eje == "fila" else 1
    a, b = origen[k], destino[k]
    lo, hi = (a, b) if a <= b else (b, a)
    return lo < corredor.indice <= hi


SEGUNDOS_DIA = 86400.0

CLIMA_MULT: dict[str, float] = {
    "despejado": 1.0,
    "normal": 1.0,
    "nublado": 1.05,
    "lluvia": 1.25,
    "lluvia_fuerte": 1.45,
    "tormenta": 1.70,
}


def _perfil_hora_default(n_franjas: int) -> np.ndarray:
    horas = np.arange(n_franjas, dtype=np.float64) * (24.0 / n_franjas)
    pico_manana = np.exp(-0.5 * ((horas - 8.5) / 2.0) ** 2)
    pico_tarde = np.exp(-0.5 * ((horas - 18.5) / 2.0) ** 2)
    return 1.0 + 0.20 * pico_manana + 0.25 * pico_tarde


class GridWorld:
    """Rejilla NxN de celdas cuadradas con distancia Manhattan y multiplicadores de congestión."""

    def __init__(
        self,
        n: int = 20,
        cell_size_m: float = 500.0,
        vehiculo: Vehiculo = Vehiculo.MOTO,
        n_franjas_hora: int = 24,
        perfil_hora: np.ndarray | None = None,
        seed: int = 0,
    ) -> None:
        self.n = n
        self.cell_size_m = float(cell_size_m)
        self.vehiculo = vehiculo
        self.n_franjas_hora = n_franjas_hora

        perfil_vehiculo = VEHICULOS[vehiculo]
        self.velocidad_base_ms = perfil_vehiculo.velocidad_base_kmh * 1000.0 / 3600.0

        n_celdas = n * n
        filas, cols = np.divmod(np.arange(n_celdas), n)
        dfila = np.abs(filas[:, None] - filas[None, :])
        dcol = np.abs(cols[:, None] - cols[None, :])
        self.dist_m = (dfila + dcol).astype(np.float64) * self.cell_size_m
        self.tiempo_base_s = self.dist_m / self.velocidad_base_ms

        if perfil_hora is None:
            perfil_hora = _perfil_hora_default(n_franjas_hora)
        self.mult_hora = perfil_hora.astype(np.float64)

        rng = np.random.default_rng(seed)
        self.densidad = rng.gamma(shape=2.0, scale=0.3, size=(n, n)).clip(0.0, 3.0)
        self.mult_zona = 1.0 + 0.4 * (self.densidad / max(float(self.densidad.max()), 1e-6))

    def _indice(self, celda: tuple[int, int]) -> int:
        fila, col = celda
        return fila * self.n + col

    def _mult_hora_en(self, t: float) -> float:
        segundos_del_dia = t % SEGUNDOS_DIA
        ancho_franja = SEGUNDOS_DIA / self.n_franjas_hora
        pos = segundos_del_dia / ancho_franja
        i0 = int(pos) % self.n_franjas_hora
        i1 = (i0 + 1) % self.n_franjas_hora
        frac = pos - int(pos)
        return float(self.mult_hora[i0] * (1.0 - frac) + self.mult_hora[i1] * frac)

    def travel(
        self,
        origen: tuple[int, int],
        destino: tuple[int, int],
        t: float,
        clima: str = "normal",
        corredores_cerrados: tuple[Corredor, ...] = (),
    ) -> tuple[float, float]:
        i, j = self._indice(origen), self._indice(destino)
        distancia_m = float(self.dist_m[i, j])
        mult_zona = 0.5 * (float(self.mult_zona.flat[i]) + float(self.mult_zona.flat[j]))
        mult_c = CLIMA_MULT.get(clima.lower() if isinstance(clima, str) else clima.value, 1.0)
        mult = mult_zona * self._mult_hora_en(t) * mult_c
        tiempo_s = float(self.tiempo_base_s[i, j]) * mult

        for corredor in corredores_cerrados:
            if _cruza_corredor(origen, destino, corredor):
                distancia_m *= corredor.factor_detour
                tiempo_s *= corredor.factor_detour
                break

        return tiempo_s, distancia_m
