"""Δt_j, Δδ_j óptimos por oferta al insertarla en el plan activo: INSERCIÓN CLÁSICA barata.
`estado.plan` se mantiene en su orden vigente; evaluar una oferta prueba insertar el par
(recogida_j, entrega_j) en cada posición válida del orden existente.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Any

from app.ai.schema import Clima
from app.ai.sequencer import Parada, Restricciones, TravelFn, _arrays_calendario, verificar_y_calendarizar

_MAX_STOPS_TOTAL = 12


@dataclass(slots=True, frozen=True)
class OfertaCandidata:
    """Oferta candidata a insertar en el plan."""

    id: str
    pos_recogida: tuple[float, float] | tuple[int, int] | Any
    pos_entrega: tuple[float, float] | tuple[int, int] | Any
    r: float
    l: Optional[float]
    theta: Optional[float]
    carga: int = 1
    expira_en: Optional[float] = None
    precio: Optional[float] = None
    anillo: Optional[int] = None
    p_gana_estimada: Optional[float] = None


@dataclass(slots=True)
class EstadoRuta:
    """Snapshot mínimo que insertion.py y feasibility.py necesitan."""

    t: float
    pos: tuple[float, float] | tuple[int, int] | Any
    clima: Clima
    plan: list[Parada]
    restricciones: Restricciones
    travel_fn: TravelFn
    ofertas: list[Optional[OfertaCandidata]] = field(default_factory=list)
    cache: dict = field(default_factory=dict)


def _clave_plan(plan: list[Parada], t: float) -> tuple:
    return (round(t, 3), tuple((p.id, p.tipo) for p in plan))


def baseline_plan(estado: EstadoRuta) -> tuple[list[int] | None, float, float, bool, int]:
    """Calendariza `estado.plan` en su orden vigente."""
    clave = _clave_plan(estado.plan, estado.t)
    if clave in estado.cache:
        return estado.cache[clave]

    if not estado.plan:
        resultado = ([], 0.0, 0.0, False, 0)
        estado.cache[clave] = resultado
        return resultado

    orden_identidad = list(range(len(estado.plan)))
    calendario = verificar_y_calendarizar(
        orden_identidad, estado.plan, estado.t, estado.pos, estado.travel_fn, estado.restricciones,
    )
    if calendario is None:
        resultado = (None, math.inf, math.inf, False, 1)
    else:
        _llegadas, salidas, dist_total = calendario
        resultado = (orden_identidad, salidas[-1] - estado.t, dist_total, False, 1)
    estado.cache[clave] = resultado
    return resultado


def _restricciones_con_oferta(restricciones: Restricciones, oferta: OfertaCandidata) -> Restricciones:
    return Restricciones(
        capacidad=restricciones.capacidad,
        r={**restricciones.r, oferta.id: oferta.r},
        l={**restricciones.l, oferta.id: oferta.l},
        theta={**restricciones.theta, oferta.id: oferta.theta},
        carga={**restricciones.carga, oferta.id: oferta.carga},
    )


def mejor_insercion(
    plan: list[Parada], oferta: OfertaCandidata, estado: EstadoRuta,
    _diagnostico: list[str] | None = None,
) -> tuple[list[Parada] | None, float, float]:
    """Prueba insertar (recogida_j, entrega_j) en cada posición válida del orden de `plan`."""
    if len(plan) + 2 > _MAX_STOPS_TOTAL:
        if _diagnostico is not None:
            _diagnostico.append("capacidad")
        return None, math.inf, math.inf

    m = len(plan)
    restricciones = _restricciones_con_oferta(estado.restricciones, oferta)
    parada_recogida = Parada(oferta.id, "recogida", oferta.pos_recogida)
    parada_entrega = Parada(oferta.id, "entrega", oferta.pos_entrega)
    paradas_todas = list(plan) + [parada_recogida, parada_entrega]
    idx_recogida, idx_entrega = m, m + 1
    arrays = _arrays_calendario(paradas_todas, restricciones)

    mejor_orden: list[int] | None = None
    mejor_tiempo = math.inf
    mejor_dist = math.inf
    for p in range(m + 1):
        for q in range(p, m + 1):
            orden = list(range(p)) + [idx_recogida] + list(range(p, q)) + [idx_entrega] + list(range(q, m))
            resultado = verificar_y_calendarizar(
                orden, paradas_todas, estado.t, estado.pos, estado.travel_fn, restricciones, arrays,
                _diagnostico,
            )
            if resultado is None:
                continue
            _llegadas, salidas, dist_total = resultado
            tiempo_total = salidas[-1] - estado.t
            if tiempo_total < mejor_tiempo:
                mejor_orden, mejor_tiempo, mejor_dist = orden, tiempo_total, dist_total

    if mejor_orden is None:
        return None, math.inf, math.inf
    return [paradas_todas[i] for i in mejor_orden], mejor_tiempo, mejor_dist


def eval_insertion(
    plan: list[Parada], oferta: OfertaCandidata, estado: EstadoRuta,
    _diagnostico: list[str] | None = None,
) -> tuple[float, float, bool]:
    """Devuelve (delta_t, delta_dist, factible). Inserción rápida."""
    if len(plan) + 2 > _MAX_STOPS_TOTAL:
        if _diagnostico is not None:
            _diagnostico.append("capacidad")
        return math.inf, math.inf, False

    _orden_base, tiempo_base, dist_base, _exacto_base, _eval_base = baseline_plan(estado)
    if _orden_base is None and plan:
        return math.inf, math.inf, False
    if not plan:
        tiempo_base, dist_base = 0.0, 0.0

    _nuevo_plan, tiempo_nuevo, dist_nuevo = mejor_insercion(plan, oferta, estado, _diagnostico)
    if _nuevo_plan is None:
        return math.inf, math.inf, False

    return tiempo_nuevo - tiempo_base, dist_nuevo - dist_base, True
