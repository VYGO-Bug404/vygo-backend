"""Dataclasses y enums del subsistema de IA de VYGO.
Compatibles con Supabase/PostGIS y el simulador HÍBRIDO.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Optional

Coordenada = tuple[float, float]


class App(IntEnum):
    UBER = 1
    DIDI = 2
    RAPPI = 3


class EstadoPedido(str, Enum):
    CREADO = "creado"
    BUSCANDO = "buscando"
    ASIGNADO = "asignado"
    EN_CAMINO = "en_camino"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"


class EstadoOferta(str, Enum):
    PENDIENTE = "pendiente"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"
    EXPIRADA = "expirada"
    PERDIDA = "perdida"
    CANCELADA = "cancelada"


class Clima(str, Enum):
    DESPEJADO = "despejado"
    NUBLADO = "nublado"
    LLUVIA = "lluvia"
    LLUVIA_FUERTE = "lluvia_fuerte"
    TORMENTA = "tormenta"
    NORMAL = "normal"
    OTRO = "otro"


CLIMA_SIMULABLE: tuple[Clima, ...] = (
    Clima.DESPEJADO,
    Clima.NUBLADO,
    Clima.LLUVIA,
    Clima.LLUVIA_FUERTE,
    Clima.TORMENTA,
)


class Vehiculo(str, Enum):
    MOTO = "moto"
    AUTO = "auto"
    BICI = "bici"


@dataclass(slots=True, frozen=True)
class PerfilVehiculo:
    capacidad: int
    velocidad_base_kmh: float
    rendimiento_max_kml: Optional[float]
    velocidad_max_rendimiento_kmh: Optional[float]


VEHICULOS: dict[Vehiculo, PerfilVehiculo] = {
    Vehiculo.MOTO: PerfilVehiculo(
        capacidad=3,
        velocidad_base_kmh=28.0,
        rendimiento_max_kml=35.0,
        velocidad_max_rendimiento_kmh=45.0,
    ),
    Vehiculo.AUTO: PerfilVehiculo(
        capacidad=4,
        velocidad_base_kmh=24.0,
        rendimiento_max_kml=14.0,
        velocidad_max_rendimiento_kmh=60.0,
    ),
    Vehiculo.BICI: PerfilVehiculo(
        capacidad=1,
        velocidad_base_kmh=16.0,
        rendimiento_max_kml=None,
        velocidad_max_rendimiento_kmh=None,
    ),
}
