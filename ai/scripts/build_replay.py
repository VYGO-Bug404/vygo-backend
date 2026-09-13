"""FASE A (NIVEL-1-DEMO-MTY.md): reproduce el turno seed 10000 (escenario índice 0 de
`scenarios/test_30.pkl`, 120 min) bajo B_SERIAL y B2, y lo vuelca a `demo/replay.json`
para que la Fase D (A* + proyección) lo consuma.

======================================================================================
NO ENVUELVAS NADA DEL HOT PATH DE SIMULACIÓN. NO METAS UN MONKEYPATCH DE
`_procesar_llegada_nodo` NI DE `_reposicionar` AQUÍ. Si "arreglas" esto añadiendo
instrumentación ahí, vas a romper la reproducción de los números oficiales SIN QUE
NINGÚN TEST TE AVISE -- el bug es silencioso y ya ocurrió una vez (ver abajo y
reports/DEMO.md, sección "Reproducibilidad").
======================================================================================

Por qué: `sequencer.held_karp` acota su enumeración exacta con un presupuesto de RELOJ
DE PARED de 25 ms (`_LIMITE_TIEMPO_EXACTO_S`), ya documentado en `reports/EVAL.md` como
sensible a contención de CPU externa. Se verificó en esta tarea que TAMBIÉN es sensible
al overhead de instrumentación dentro del hot path: envolver `_procesar_llegada_nodo`
con un monkeypatch de INSTANCIA -- incluso de sólo lectura, sin mutar nada -- bastó para
desplazar qué secuencias evalúa `held_karp` antes de agotar su presupuesto, lo que
cambió el resultado real de VYGO de 888.74 MXN/16 entregas a 737.39 MXN/13 entregas en
una prueba real. Por eso este script llama `evaluate.correr_escenario_con_paradas` TAL
CUAL -- es la ÚNICA forma verificada de reproducir 253.95/5 y 888.74/16 exactos.

Consecuencias de diseño, todas para no tocar el hot path:

- MOVE no es un evento en este JSON: se deriva de posiciones consecutivas en `paradas`
  (dos entradas seguidas con celda distinta implican un tramo de movimiento). Fase D ya
  hace esto por su cuenta (A* entre paradas consecutivas).
- WAIT no es un evento en este JSON. Se deriva en la Fase E, al pintar, con:
      espera_s = (t_llegada[i+1] - t_llegada[i]) - segundos_de_Astar[i -> i+1]
  Si es positiva, el repartidor llega y se queda parado (espera de preparación); si es
  <=0, viaja todo el tramo. Cero instrumentación aquí, cero riesgo de repetir el bug de
  arriba.
- `frescura_restante_min` se deriva por POST-PROCESAMIENTO de la lista `paradas` que YA
  devuelve `correr_escenario_con_paradas` (t_min, tipo, pedido, pos, ingreso) -- nunca
  releyendo `env._llegadas_cache` en vivo (eso también se probó y es lo que causó el
  hallazgo de arriba) ni volviendo a correr el entorno para esto.
- `pedidos` (diccionario raíz, TODOS los pedidos del turno): sí requiere una corrida más
  del entorno para leer `env.pedidos` al final -- no hay forma de sacarlo de
  `correr_escenario_con_paradas` sin modificarla, y no se modifica (no está en la lista
  de "congelado" pero tampoco en la de archivos nuevos permitidos: no se toca). Esa
  corrida adicional NO envuelve nada tampoco (mismo motivo), y su propio resultado
  financiero se descarta por completo -- sólo importa `env.pedidos` al final, que es
  seguro de usar así: se verificó empíricamente antes de escribir este script que el
  stream de pedidos es un proceso de fondo independiente de la política (B_SERIAL y B2
  generaron los mismos 11200 pedidos, contenido idéntico, en este escenario), así que no
  importa si esta corrida de cosecha diverge en ruteo por el mismo timing de held_karp --
  el contenido de los pedidos no depende de eso. El diccionario `pedidos` que se escribe
  en el JSON se FILTRA a la unión de los `pedido_id` que aparecen en `serial.paradas` y
  `vygo.paradas` (21 de 11200 en este escenario) -- este JSON se embebe en el HTML de la
  Fase E y las demás entradas no las usa nadie. El conteo real (11200) queda en
  `meta.pedidos_generados_total`, no se pierde.

DECISIÓN DE DISEÑO -- `"decisiones": []` aquí es intencional, no un pendiente sin
resolver: el trío (delta_f, delta_t, ratio, rho_ref, aceptado, p_gana, anillo) se
reconstruye POST-HOC, en frío, en `ai/scripts/build_nav.py` (Fase D), sobre el plan YA
CONGELADO -- ahí el simulador no está corriendo, no hay presupuesto de reloj de pared de
por medio y por lo tanto no hay riesgo de reproducibilidad. Sólo se reconstruye para
pedidos ACEPTADOS (delta_f = pago real ya en `replay.json`; delta_t = minutos del plan
CON el pedido menos minutos del plan SIN él, con tiempos reales de A*; rho_ref = tasa
REALIZADA del turno = total_mxn / horas, que es el enunciado correcto de la regla de
umbral, no un atajo). Los rechazos no son recuperables post-hoc (no se sabe qué otras
ofertas aparecieron en cada ronda) y no se inventan -- el panel de la Fase E sólo
mostrará aceptaciones, y lo dirá explícitamente ("economía de cada aceptación"). Ver
`reports/DEMO.md` para el detalle completo de esta decisión.

Uso: python -m ai.scripts.build_replay   (o `python ai/scripts/build_replay.py` desde ai/)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

_AI_ROOT = Path(__file__).resolve().parent.parent
if str(_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_ROOT))

from vygo.baselines import RhoHatMovil  # noqa: E402
from vygo.congelar_escenarios import EscenarioCongelado, cargar_escenarios  # noqa: E402
from vygo.env import VygoEnv  # noqa: E402
from vygo.eventos import EventoSurge, ProgramadorEventos  # noqa: E402
from vygo.evaluate import (  # noqa: E402
    MAX_PASOS_ESCENARIO,
    _b2,
    _b_serial,
    correr_escenario_con_paradas,
)

RUTA_REPLAY = _AI_ROOT / "demo" / "replay.json"
INDICE_ESCENARIO = 0  # seed 10000: primer escenario de scenarios/test_30.pkl


def _procesar_paradas(paradas_crudas: list[dict], theta_min_de: dict[str, float]) -> list[dict]:
    """Post-procesa la lista `paradas` que YA devuelve `correr_escenario_con_paradas`
    (t_min, tipo 'recogida'/'entrega', pedido, pos, ingreso) al esquema de esta tarea
    (P/D, celda_x/y, pago_mxn, frescura_restante_min). NO vuelve a tocar el entorno."""

    salida: list[dict] = []
    t_recogida_de: dict[str, float] = {}
    for p in paradas_crudas:
        pid = p["pedido"]
        tipo = "P" if p["tipo"] == "recogida" else "D"
        theta_min = theta_min_de.get(pid)

        if tipo == "P":
            t_recogida_de[pid] = p["t_min"]
            frescura = theta_min
            pago = None
        else:
            t0 = t_recogida_de.get(pid, p["t_min"])
            frescura = None if theta_min is None else round(theta_min - (p["t_min"] - t0), 2)
            pago = round(p["ingreso"], 2) if p["ingreso"] else None

        salida.append({
            "t_min": round(p["t_min"], 2),
            "tipo": tipo,
            "pedido_id": pid,
            "celda_x": int(p["pos"][0]),
            "celda_y": int(p["pos"][1]),
            "pago_mxn": pago,
            "frescura_restante_min": frescura,
        })
    return salida


def _cosechar_pedidos(escenario: EscenarioCongelado) -> dict[str, dict]:
    """TODOS los pedidos que el generador creó en el turno (no sólo los aceptados). Ver
    docstring del módulo: corrida adicional SIN envolver nada, resultado financiero
    descartado -- sólo se lee `env.pedidos` al final."""

    programador = ProgramadorEventos(list(escenario.eventos)) if escenario.eventos else None
    env = VygoEnv(
        nivel=escenario.nivel, m_comercios=escenario.m_comercios,
        duracion_turno_s=escenario.duracion_turno_s, programador_eventos=programador,
    )
    obs, info = env.reset(seed=escenario.seed)
    rho_movil = RhoHatMovil()
    for _ in range(MAX_PASOS_ESCENARIO):
        estado = env._estado_ruta()
        mask = info["action_mask"]
        accion = _b2(estado, obs, mask, rho_movil.valor)
        obs, r, term, trunc, info = env.step(accion)
        rho_movil.actualizar(env.t, r)
        if term or trunc:
            break
    return {pid: round(p.theta_frescura / 60.0, 2) for pid, p in env.pedidos.items()}


def construir_replay() -> dict:
    escenarios = cargar_escenarios()
    escenario = escenarios[INDICE_ESCENARIO]

    # Llamadas TAL CUAL -- ver advertencia en el docstring del módulo.
    resultado_serial = correr_escenario_con_paradas(escenario, _b_serial)
    resultado_vygo = correr_escenario_con_paradas(escenario, _b2)

    theta_min_de = _cosechar_pedidos(escenario)

    grid_temporal = VygoEnv(nivel=escenario.nivel, m_comercios=escenario.m_comercios)
    grid_temporal.reset(seed=escenario.seed)
    escala_km_por_celda = grid_temporal.grid.cell_size_m / 1000.0

    surge_min: Optional[float] = None
    for ev in escenario.eventos:
        if isinstance(ev, EventoSurge):
            surge_min = ev.inicia_min
            break

    paradas_serial = _procesar_paradas(resultado_serial["paradas"], theta_min_de)
    paradas_vygo = _procesar_paradas(resultado_vygo["paradas"], theta_min_de)

    # `pedidos` sólo trae los que de verdad aparecen en alguna de las dos secuencias
    # congeladas (21 de 11200 en este escenario) -- este JSON se va a embeber en el HTML
    # de la Fase E, y las otras ~11179 entradas no las usa nadie. El conteo original
    # queda en meta.pedidos_generados_total para no perder la cifra real del generador.
    ids_usados = {p["pedido_id"] for p in paradas_serial} | {p["pedido_id"] for p in paradas_vygo}
    pedidos_json = {pid: {"theta_min": theta_min_de[pid]} for pid in ids_usados}

    def _empaquetar(paradas: list[dict], resultado: dict) -> dict:
        return {
            "paradas": paradas,
            "decisiones": [],  # decisión de diseño -- ver docstring del módulo
            "total_mxn": round(resultado["ingreso"], 2),
            "entregas": int(resultado["entregados"]),
        }

    return {
        "meta": {
            "seed": escenario.seed,
            "duracion_min": escenario.duracion_turno_s / 60.0,
            "theta_rango_min": [15, 40],  # documentación: rango real de generator.py, no un valor fijo
            "surge_min": surge_min,
            "escala_km_por_celda": escala_km_por_celda,
            "pedidos_generados_total": len(theta_min_de),
        },
        "pedidos": pedidos_json,
        "serial": _empaquetar(paradas_serial, resultado_serial),
        "vygo": _empaquetar(paradas_vygo, resultado_vygo),
    }


if __name__ == "__main__":
    datos = construir_replay()

    print(f"serial: total_mxn={datos['serial']['total_mxn']}  entregas={datos['serial']['entregas']}")
    print(f"vygo:   total_mxn={datos['vygo']['total_mxn']}  entregas={datos['vygo']['entregas']}")

    RUTA_REPLAY.parent.mkdir(parents=True, exist_ok=True)
    RUTA_REPLAY.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    print(f"escrito {RUTA_REPLAY} ({RUTA_REPLAY.stat().st_size / 1024:.1f} KB)")
