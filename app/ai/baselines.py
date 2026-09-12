"""Políticas de decisión:
B2 / HÍBRIDO: Regla analítica Bellman con p_gana y umbral rho_hat.
B1: Primera factible.
B_SERIAL: Sin VYGO (una app a la vez, sin agrupamiento).
B0: Aleatoria factible.
"""

from __future__ import annotations

import math
import numpy as np

from app.ai.feasibility import CONTADOR_MOTIVOS, K_F, action_mask
from app.ai.insertion import EstadoRuta, eval_insertion
from app.ai.sequencer import n_pedidos_en_plan

COSTO_KM_MXN = 1.2


class RhoHatMovil:
    """Media móvil de la tasa de ganancia realizada sobre una ventana de tiempo."""

    def __init__(self, ventana_s: float = 90 * 60.0, inicial: float = 140.0) -> None:
        self.ventana_s = ventana_s
        self.valor = inicial
        self._eventos: list[tuple[float, float]] = []

    def actualizar(self, t: float, ingreso: float) -> None:
        self._eventos.append((t, ingreso))
        corte = t - self.ventana_s
        while self._eventos and self._eventos[0][0] < corte:
            self._eventos.pop(0)
        total = sum(g for _, g in self._eventos)
        horas = min(t, self.ventana_s) / 3600.0
        if horas > 0:
            self.valor = total / horas


def politica_aleatoria(estado: EstadoRuta, rng: np.random.Generator) -> int:
    """B0: acción uniforme entre las que la máscara permite."""
    mask = action_mask(estado)
    validas = np.flatnonzero(mask)
    return int(rng.choice(validas)) if len(validas) else K_F


def politica_primera_factible(estado: EstadoRuta) -> int:
    """B1: acepta la primera oferta factible en orden de slot."""
    mask = action_mask(estado)
    for i in range(K_F):
        if mask[i]:
            return i
    return K_F


def politica_serial(estado: EstadoRuta) -> int:
    """B_SERIAL: el repartidor sin VYGO -- a lo más un pedido a bordo."""
    if n_pedidos_en_plan(estado.plan) >= 1:
        return K_F
    mask = action_mask(estado)
    for i in range(K_F):
        if mask[i]:
            return i
    return K_F


def _tasa_marginal(estado: EstadoRuta, i: int, con_p_gana: bool) -> tuple[float, bool]:
    oferta = estado.ofertas[i]
    if oferta is None:
        return -math.inf, False
    delta_t, delta_dist, factible = eval_insertion(estado.plan, oferta, estado)
    if not factible or delta_t <= 0:
        return -math.inf, False
    # delta_dist en metros o km
    delta_dist_km = (delta_dist / 1000.0) if delta_dist > 50.0 else delta_dist
    delta_t_horas = (delta_t / 3600.0) if delta_t > 120.0 else (delta_t / 60.0)
    valor_marginal = (oferta.precio or 0.0) - COSTO_KM_MXN * delta_dist_km
    tasa = valor_marginal / max(delta_t_horas, 0.0083)  # min 30s
    if con_p_gana:
        tasa *= oferta.p_gana_estimada if oferta.p_gana_estimada is not None else 1.0
    return tasa, True


def politica_umbral(
    estado: EstadoRuta, rho_hat: float, con_p_gana: bool = True, instrumentar: bool = False,
) -> int:
    """HÍBRIDO / B2: maximiza p_gana_j * (precio_j - c_kappa*delta_dist_j) / delta_t_j
    y acepta esa oferta si supera `rho_hat`; si ninguna supera el umbral, rechazar_todas (K_F).
    """
    mask = action_mask(estado, instrumentar=instrumentar)
    n_pedidos_plan = n_pedidos_en_plan(estado.plan)
    diag_activo = instrumentar and n_pedidos_plan >= 1

    candidatas: list[tuple[int, float]] = []
    for i in range(K_F):
        if not mask[i]:
            continue
        tasa, ok = _tasa_marginal(estado, i, con_p_gana)
        if ok:
            candidatas.append((i, tasa))

    mejor_i, mejor_tasa = None, rho_hat
    for i, tasa in candidatas:
        if tasa > mejor_tasa:
            mejor_tasa, mejor_i = tasa, i

    if diag_activo:
        for i, _tasa in candidatas:
            if i != mejor_i:
                CONTADOR_MOTIVOS["umbral_rho"] += 1
        if mejor_i is not None:
            CONTADOR_MOTIVOS["aceptada"] += 1

    return mejor_i if mejor_i is not None else K_F
