"""Subsistema de Inteligencia Artificial de VYGO.
Implementación oficial de la política HÍBRIDO y el secuenciador exacto Held-Karp con Numba.
"""

from app.ai.sequencer import (
    held_karp,
    verificar_y_calendarizar,
    Parada,
    Restricciones,
    TravelFn,
    n_pedidos_en_plan,
)
from app.ai.insertion import (
    OfertaCandidata,
    EstadoRuta,
    baseline_plan,
    mejor_insercion,
    eval_insertion,
)
from app.ai.feasibility import (
    action_mask,
    holguras_frescura_plan,
    K_F,
    K_A_MAXIMO,
)
from app.ai.baselines import (
    politica_umbral,
    politica_primera_factible,
    politica_serial,
    politica_aleatoria,
    RhoHatMovil,
)
from app.ai.geo import (
    travel_fn_monterrey,
    GridWorld,
)

__all__ = [
    "held_karp",
    "verificar_y_calendarizar",
    "Parada",
    "Restricciones",
    "TravelFn",
    "n_pedidos_en_plan",
    "OfertaCandidata",
    "EstadoRuta",
    "baseline_plan",
    "mejor_insercion",
    "eval_insertion",
    "action_mask",
    "holguras_frescura_plan",
    "K_F",
    "K_A_MAXIMO",
    "politica_umbral",
    "politica_primera_factible",
    "politica_serial",
    "politica_aleatoria",
    "RhoHatMovil",
    "travel_fn_monterrey",
    "GridWorld",
]
