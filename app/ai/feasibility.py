"""Máscara de factibilidad exacta (frescura, capacidad, precedencia).
violaciones_frescura debe ser 0 SIEMPRE.
Enmascara en lugar de penalizar.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np

from app.ai.insertion import EstadoRuta, OfertaCandidata, baseline_plan, eval_insertion
from app.ai.sequencer import n_pedidos_en_plan, verificar_y_calendarizar

K_F = 8
K_A_MAXIMO = 4
N_PREFILTRO = 3
HOLGURA_MINIMA_REPOSICIONAR_S = 5 * 60.0

CONTADOR_MOTIVOS: Counter = Counter()


def reset_contador_motivos() -> None:
    CONTADOR_MOTIVOS.clear()


def holguras_frescura_plan(estado: EstadoRuta) -> list[float]:
    """Holgura de frescura (theta_i - (T_entrega - S_recogida)) de cada pedido del plan."""
    if not estado.plan:
        return []

    orden, _tiempo, _dist, _exacto, _evaluadas = baseline_plan(estado)
    if orden is None:
        return []

    resultado = verificar_y_calendarizar(
        orden, estado.plan, estado.t, estado.pos, estado.travel_fn, estado.restricciones,
    )
    if resultado is None:
        return []
    llegadas, salidas, _dist_total = resultado

    pos_recogida: dict[str, int] = {}
    pos_entrega: dict[str, int] = {}
    for k, idx in enumerate(orden):
        parada = estado.plan[idx]
        if parada.tipo in ("recogida", "recoleccion"):
            pos_recogida[parada.id] = k
        else:
            pos_entrega[parada.id] = k

    holguras = []
    for pid, k_e in pos_entrega.items():
        theta = estado.restricciones.theta_de(pid)
        if theta is None:
            continue
        if pid in pos_recogida:
            k_r = pos_recogida[pid]
            holguras.append(theta - (llegadas[k_e] - salidas[k_r]))
        else:
            # Ya recogido: medir desde t0
            holguras.append(theta - (llegadas[k_e] - estado.t))
    return holguras


def _puntaje_prefiltro(oferta: OfertaCandidata, estado: EstadoRuta) -> float:
    """Desvío aproximado / tarifa. Menor es mejor."""
    pos_est = (estado.pos.lat, estado.pos.lon) if hasattr(estado.pos, 'lat') else estado.pos
    pos_rec = (oferta.pos_recogida.lat, oferta.pos_recogida.lon) if hasattr(oferta.pos_recogida, 'lat') else oferta.pos_recogida
    pos_ent = (oferta.pos_entrega.lat, oferta.pos_entrega.lon) if hasattr(oferta.pos_entrega, 'lat') else oferta.pos_entrega

    dist_recogida = math.hypot(pos_est[0] - pos_rec[0], pos_est[1] - pos_rec[1])
    dist_entrega = math.hypot(pos_rec[0] - pos_ent[0], pos_rec[1] - pos_ent[1])
    precio = oferta.precio if oferta.precio else 1.0
    return (dist_recogida + dist_entrega) / max(precio, 1e-6)


def action_mask(estado: EstadoRuta, instrumentar: bool = False) -> np.ndarray:
    """Shape (K_F + 2,), dtype bool.
    K_F=8 ofertas visibles, luego rechazar_todas, reposicionarse.
    """
    mask = np.zeros(K_F + 2, dtype=bool)
    n_pedidos_plan = n_pedidos_en_plan(estado.plan)
    diag_activo = instrumentar and n_pedidos_plan >= 1

    if n_pedidos_plan < K_A_MAXIMO:
        candidatos = []
        for i in range(K_F):
            oferta = estado.ofertas[i] if i < len(estado.ofertas) else None
            if oferta is None:
                continue
            if oferta.expira_en is not None and oferta.expira_en <= estado.t:
                continue
            candidatos.append((i, oferta))

        candidatos.sort(key=lambda par: _puntaje_prefiltro(par[1], estado))
        for i, oferta in candidatos[:N_PREFILTRO]:
            diag: list[str] = []
            _dt, _dd, factible = eval_insertion(
                estado.plan, oferta, estado, diag if diag_activo else None,
            )
            mask[i] = factible
            if diag_activo and not factible:
                motivo = Counter(diag).most_common(1)[0][0] if diag else "capacidad"
                CONTADOR_MOTIVOS[motivo] += 1
        if diag_activo:
            CONTADOR_MOTIVOS["prefiltro"] += max(0, len(candidatos) - N_PREFILTRO)
    elif diag_activo:
        CONTADOR_MOTIVOS["tope_ka"] += len(estado.ofertas)

    mask[K_F] = True  # rechazar_todas: siempre disponible

    holguras = holguras_frescura_plan(estado)
    mask[K_F + 1] = not any(h < HOLGURA_MINIMA_REPOSICIONAR_S for h in holguras)

    return mask
