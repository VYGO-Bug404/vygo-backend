import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from app.core.schemas import (
    Punto,
    RepartidorEstado,
    PedidoActivo,
    OfertaEntrante,
    Contexto,
    DecisionOferta,
    Economia,
    Riesgo,
    Plan,
    Telemetria,
    Alerta,
    Politica,
)
from app.core.metrics import (
    distancia_vial_km,
    tiempo_viaje_min,
    calcular_costo_marginal,
    calcular_tasa_marginal,
    clasificar_zona,
    es_zona_alta_demanda,
)
from app.core.router import (
    generar_items_paradas,
    resolver_secuencia_optima,
    construir_plan,
)

logger = logging.getLogger('vygo.policies')

def evaluar_ajuste_aprendido_ppo(
    oferta: OfertaEntrante,
    contexto: Optional[Contexto],
    holgura_frescura_min: float,
) -> float:
    """
    Calcula el ajuste aprendido h*(S) por valor posicional, evento surge y riesgo de cascada.
    """
    ajuste = 0.0
    zona_destino = clasificar_zona(oferta.destino)

    # 1. Valor posicional: si deja en polo gastronómico de alta demanda
    if es_zona_alta_demanda(oferta.destino):
        if zona_destino == "san_pedro":
            ajuste += 18.0
        elif zona_destino == "centro":
            ajuste += 14.0
        elif zona_destino == "tec":
            ajuste += 12.0
    elif zona_destino == "cumbres":
        ajuste += 5.0
    else:
        # Periferia: penalización por retorno vacío / páramo
        ajuste -= 16.0

    # 2. Surge activo en zona
    if contexto and contexto.evento_activo == "surge":
        if clasificar_zona(oferta.origen) == "centro" or zona_destino == "centro":
            ajuste += 22.0

    # 3. Riesgo de cascada y holgura de frescura
    if holgura_frescura_min < 7.0:
        ajuste -= 15.0
    elif holgura_frescura_min > 15.0:
        ajuste += 4.0

    return round(ajuste, 1)

def normalizar_politica(pol: Optional[str]) -> Tuple[str, str]:
    """
    Retorna (politica_interna, politica_salida_v2).
    Reconcilia 'PPO', 'HIBRIDO', 'B1', 'B2' con 'agente_ppo', 'B2_umbral', 'B1_simple'.
    """
    if not pol:
        return "agente_ppo", "PPO"
    p = str(pol).strip()
    p_upper = p.upper()
    if p_upper in ("PPO", "AGENTE_PPO"):
        pol_out = "PPO" if p_upper == "PPO" else "agente_ppo"
        return "agente_ppo", pol_out
    elif p_upper in ("HIBRIDO", "B2_UMBRAL", "B2"):
        pol_out = "HIBRIDO" if p_upper in ("HIBRIDO", "B2") else "B2_umbral"
        return "B2_umbral", pol_out
    elif p_upper in ("B1", "B1_SIMPLE"):
        pol_out = "B1" if p_upper == "B1" else "B1_simple"
        return "B1_simple", pol_out
    elif p_upper in ("AGENTE_BC", "BC"):
        return "agente_bc", "agente_bc"
    return p, p

def evaluar_oferta(
    repartidor: RepartidorEstado,
    plan_activo: List[PedidoActivo],
    oferta: OfertaEntrante,
    contexto: Optional[Contexto],
    politica: Politica,
    t0: datetime,
) -> Tuple[DecisionOferta, Optional[List]]:
    """
    Evalúa una oferta entrante respecto al estado actual y devuelve la decisión con métricas.
    Totalmente compatible con Contrato v1.0 y Contrato v2.0 (§5).
    """
    pol_interna, pol_v2 = normalizar_politica(politica)
    clima = contexto.clima if contexto and contexto.clima else "normal"
    capacidad = repartidor.capacidad

    # Caso base sin la oferta
    items_base, carga_base = generar_items_paradas(plan_activo, None, t0)
    sec_base, dist_base, dur_base, _, _ = resolver_secuencia_optima(
        repartidor.posicion, items_base, carga_base, capacidad_max=capacidad, clima=clima, t0=t0
    )

    # Caso incorporando la oferta
    if pol_interna == "B1_simple" and len(plan_activo) >= 1:
        sec_comb = None
        motivo_inf = "capacidad"
    else:
        items_comb, carga_comb = generar_items_paradas(plan_activo, oferta, t0)
        sec_comb, dist_comb, dur_comb, evals_comb, motivo_inf = resolver_secuencia_optima(
            repartidor.posicion, items_comb, carga_comb, capacidad_max=capacidad, clima=clima, t0=t0
        )

    rho_actual = repartidor.rho_actual_mxn_h

    # Extraer propina estimada de contexto si existe
    propina_esperada = 0.0
    if oferta.contexto:
        ctx_dict = oferta.contexto if isinstance(oferta.contexto, dict) else oferta.contexto.model_dump()
        propina_esperada = float(ctx_dict.get("propina_esperada_mxn") or 0.0)

    # Determinar anillo y p_gana de la oferta (Contrato v2.0 §5.1 & ai/vygo/baselines.py)
    anillo = oferta.anillo or (1 if (oferta.radio_metros or 1500) <= 1500 else (2 if (oferta.radio_metros or 1500) <= 3000 else 3))
    ctx_p_gana = None
    if oferta.contexto:
        ctx_d = oferta.contexto if isinstance(oferta.contexto, dict) else oferta.contexto.model_dump()
        ctx_p_gana = ctx_d.get("p_gana") or ctx_d.get("p_gana_estimada")
    p_gana = float(ctx_p_gana) if ctx_p_gana is not None else (0.85 if anillo == 1 else (0.60 if anillo == 2 else 0.35))

    # Si no es factible
    if sec_comb is None:
        d_directa = distancia_vial_km(repartidor.posicion, oferta.origen) + distancia_vial_km(oferta.origen, oferta.destino)
        t_directo = tiempo_viaje_min(d_directa, clima)
        c_marg = calcular_costo_marginal(d_directa, t_directo)
        costo_km = round(d_directa * 2.50, 2)
        costo_tiempo = round(t_directo * 0.50, 2)
        g_neta = oferta.precio_mxn + propina_esperada - c_marg
        t_marg = calcular_tasa_marginal(g_neta, t_directo)
        if pol_interna == "B2_umbral":
            t_marg = round(t_marg * p_gana, 1)

        economia = Economia(
            tarifa_mxn=round(oferta.precio_mxn, 2),
            delta_tiempo_min=round(t_directo, 1),
            delta_distancia_km=round(d_directa, 1),
            costo_marginal_mxn=round(c_marg, 2),
            ganancia_neta_mxn=round(g_neta, 2),
            tasa_marginal_mxn_h=round(t_marg, 1),
            rho_actual_mxn_h=round(rho_actual, 1),
            ajuste_aprendido_mxn_h=0.0,
            umbral_superado=False,
            tarifa=round(oferta.precio_mxn, 2),
            propina_esperada=round(propina_esperada, 2),
            costo_km=costo_km,
            costo_tiempo=costo_tiempo,
            ganancia_neta=round(g_neta, 2),
        )
        riesgo = Riesgo(
            holgura_frescura_min=0.0,
            holgura_limite_min=0.0,
            prob_entrega_a_tiempo=0.10,
            p_gana=p_gana,
            anillo=anillo,
            prob_retraso=0.90,
            frescura_restante=0.0,
            holgura=0.0,
            desvio_km=round(d_directa, 1),
        )
        dec = DecisionOferta(
            oferta_id=oferta.oferta_id,
            pedido_id=oferta.pedido_id,
            app=oferta.app,  # type: ignore
            decision="rechazar",
            prioridad=1,
            confianza=0.95,
            economia=economia,
            riesgo=riesgo,
            factible=False,
            motivo_infactible=motivo_inf,
            explicacion_corta=f"Infactible: {motivo_inf}",
            explicacion=f"Rechaza: la oferta excede la restricción operativa de {motivo_inf}.",
            aceptar=False,
            tasa_marginal=round(t_marg, 1),
            rho_actual=round(rho_actual, 1),
            ajuste_aprendido=0.0,
            politica=pol_v2,  # type: ignore
        )
        return dec, None

    # Caso factible
    delta_km = max(0.1, dist_comb - dist_base)
    delta_min = max(0.5, dur_comb - dur_base)
    costo_marg = calcular_costo_marginal(delta_km, delta_min)
    costo_km = round(delta_km * 2.50, 2)
    costo_tiempo = round(delta_min * 0.50, 2)
    ganancia_neta = oferta.precio_mxn + propina_esperada - costo_marg
    tasa_marginal = calcular_tasa_marginal(ganancia_neta, delta_min)

    # Extraer holguras para la entrega de la oferta
    holgura_frescura = 15.0
    holgura_limite = 20.0
    espera_cocina = 0.0
    tipo_prod = "caliente"
    if oferta.contexto:
        ctx_d = oferta.contexto if isinstance(oferta.contexto, dict) else oferta.contexto.model_dump()
        tipo_prod = ctx_d.get("tipo_producto", "caliente")

    es_no_perecedero = (tipo_prod == "no_perecedero")

    for s in sec_comb:
        it = s["item"]
        if it.pedido_id == oferta.pedido_id:
            if it.tipo == "recoleccion":
                espera_cocina = s.get("espera_m", 0.0)
            elif it.tipo == "entrega":
                if s.get("holgura_frescura_min") is not None:
                    holgura_frescura = s["holgura_frescura_min"]
                holgura_limite = max(0.0, it.limite_min - s["eta_min"])

    prob_a_tiempo = min(0.98, max(0.50, 0.75 + (holgura_limite / 60.0) * 0.25))

    # Evaluación según política
    ajuste_aprendido = 0.0
    if pol_interna == "agente_ppo":
        ajuste_aprendido = evaluar_ajuste_aprendido_ppo(oferta, contexto, holgura_frescura)
        tasa_evaluada = tasa_marginal + ajuste_aprendido
        umbral_superado = tasa_evaluada >= rho_actual
        if len(plan_activo) == 0 and tasa_evaluada >= 115.0:
            umbral_superado = True
    elif pol_interna == "B2_umbral":
        # HÍBRIDO: regla analítica Bellman con p_gana, ajuste_aprendido es estrictamente 0.0 (Contrato v2.0 §1 & §5.1)
        # tasa_marginal = p_gana * (tarifa + propina - costo) / dt_horas
        ajuste_aprendido = 0.0
        tasa_marginal = round(tasa_marginal * p_gana, 1)
        tasa_evaluada = tasa_marginal
        umbral_superado = tasa_marginal >= rho_actual
    elif pol_interna == "B1_simple":
        # B1 acepta todo lo factible dentro de su capacidad (sin umbral)
        ajuste_aprendido = 0.0
        tasa_evaluada = tasa_marginal
        umbral_superado = True
    else:  # Fallback
        ajuste_aprendido = 0.0
        tasa_marginal = round(tasa_marginal * p_gana, 1)
        tasa_evaluada = tasa_marginal
        umbral_superado = tasa_marginal >= rho_actual

    decision_str = "aceptar" if umbral_superado else "rechazar"

    economia = Economia(
        tarifa_mxn=round(oferta.precio_mxn, 2),
        delta_tiempo_min=round(delta_min, 1),
        delta_distancia_km=round(delta_km, 1),
        costo_marginal_mxn=round(costo_marg, 2),
        ganancia_neta_mxn=round(ganancia_neta, 2),
        tasa_marginal_mxn_h=round(tasa_marginal, 1),
        rho_actual_mxn_h=round(rho_actual, 1),
        ajuste_aprendido_mxn_h=round(ajuste_aprendido, 1),
        umbral_superado=umbral_superado,
        tarifa=round(oferta.precio_mxn, 2),
        propina_esperada=round(propina_esperada, 2),
        costo_km=costo_km,
        costo_tiempo=costo_tiempo,
        ganancia_neta=round(ganancia_neta, 2),
    )
    riesgo = Riesgo(
        holgura_frescura_min=round(holgura_frescura, 1) if not es_no_perecedero else 99999.0,
        holgura_limite_min=round(holgura_limite, 1),
        holgura_espera_min=round(espera_cocina, 1),
        prob_entrega_a_tiempo=round(prob_a_tiempo, 2),
        p_gana=p_gana,
        anillo=anillo,
        prob_retraso=round(max(0.0, min(1.0, 1.0 - prob_a_tiempo)), 2),
        frescura_restante=round(holgura_frescura, 1) if not es_no_perecedero else None,
        holgura=round(espera_cocina, 1),
        desvio_km=round(delta_km, 1),
    )

    diff = tasa_marginal - rho_actual
    signo = "+" if diff >= 0 else ""
    if decision_str == "aceptar":
        explicacion_corta = f"{signo}${tasa_marginal:.0f}/h vs tu ${rho_actual:.0f}/h"
        if pol_interna == "agente_ppo":
            zona_dest = clasificar_zona(oferta.destino).upper()
            explicacion = (
                f"Acepta: paga a ${tasa_marginal:.1f}/h contra tu promedio de ${rho_actual:.1f}/h de hoy, "
                f"con ajuste posicional de {ajuste_aprendido:+.1f} MXN/h hacia {zona_dest}. "
                f"Agrega sólo {delta_km:.1f} km y deja {holgura_frescura:.1f} min de margen de frescura."
            )
        else:
            explicacion = (
                f"Acepta: tasa marginal de ${tasa_marginal:.1f}/h supera tu umbral actual de ${rho_actual:.1f}/h. "
                f"Agrega {delta_km:.1f} km y {delta_min:.1f} min."
            )
    else:
        # Según plantilla oficial §5.1: «Rechazado: te paga a $128/h, tu promedio hoy es $141/h»
        explicacion_corta = f"Rechazado: te paga a ${tasa_marginal:.0f}/h, tu promedio hoy es ${rho_actual:.0f}/h"
        explicacion = (
            f"Rechaza: la tasa (${tasa_marginal:.1f}/h) queda por debajo de tu promedio (${rho_actual:.1f}/h). "
            f"El desvío de {delta_km:.1f} km diluye tu ingreso horario."
        )

    dec = DecisionOferta(
        oferta_id=oferta.oferta_id,
        pedido_id=oferta.pedido_id,
        app=oferta.app,  # type: ignore
        decision=decision_str,  # type: ignore
        prioridad=1,
        confianza=0.88 if pol_interna == "agente_ppo" else 0.95,
        economia=economia,
        riesgo=riesgo,
        factible=True,
        motivo_infactible=None,
        explicacion_corta=explicacion_corta,
        explicacion=explicacion,
        aceptar=(decision_str == "aceptar"),
        tasa_marginal=round(tasa_marginal, 1),
        rho_actual=round(rho_actual, 1),
        ajuste_aprendido=round(ajuste_aprendido, 1),
        politica=pol_v2,  # type: ignore
    )

    return dec, sec_comb

def procesar_decisiones(
    repartidor: RepartidorEstado,
    plan_activo: List[PedidoActivo],
    ofertas: List[OfertaEntrante],
    contexto: Optional[Contexto],
    politica_solicitada: Politica,
    t0: datetime,
) -> Tuple[Politica, List[DecisionOferta], Plan, Telemetria, List[Alerta]]:
    """
    Ejecuta el evaluador para todas las ofertas con Circuit Breaker automático hacia B2_umbral.
    """
    politica_efectiva = politica_solicitada
    alertas: List[Alerta] = []

    decisiones: List[DecisionOferta] = []
    ofertas_aceptadas: List[OfertaEntrante] = []

    for of in ofertas:
        try:
            dec, sec_comb = evaluar_oferta(
                repartidor, plan_activo, of, contexto, politica_efectiva, t0
            )
            decisiones.append(dec)
            if dec.decision == "aceptar":
                ofertas_aceptadas.append(of)
        except Exception as ex:
            pol_fallback: Politica = "HIBRIDO" if str(politica_efectiva).upper() in ("PPO", "HIBRIDO") else "B2_umbral"
            logger.warning(f"Fallo en evaluacion con {politica_efectiva}: {ex}. Activando Circuit Breaker a {pol_fallback}.")
            politica_efectiva = pol_fallback
            alertas.append(
                Alerta(
                    nivel="aviso",
                    codigo="riesgo_retraso",
                    mensaje=f"Degradación elegante activada: conmutando a política analítica {pol_fallback}."
                )
            )
            # Reintentar con política analítica de respaldo
            dec, sec_comb = evaluar_oferta(
                repartidor, plan_activo, of, contexto, pol_fallback, t0
            )
            decisiones.append(dec)
            if dec.decision == "aceptar":
                ofertas_aceptadas.append(of)

    # Construir el plan de ruta resultante
    # Si hay ofertas aceptadas, incorporamos la de mayor prioridad/ganancia
    clima = contexto.clima if contexto and contexto.clima else "normal"
    capacidad = repartidor.capacidad

    ingreso_plan_base = sum(getattr(pa, "precio_mxn", None) or 60.0 for pa in plan_activo)
    if ofertas_aceptadas:
        mejor_oferta = max(ofertas_aceptadas, key=lambda o: o.precio_mxn)
        items_final, carga_final = generar_items_paradas(plan_activo, mejor_oferta, t0)
        sec_final, dist_f, dur_f, evals_f, _ = resolver_secuencia_optima(
            repartidor.posicion, items_final, carga_final, capacidad_max=capacidad, clima=clima, t0=t0
        )
        ingreso_estimado = ingreso_plan_base + mejor_oferta.precio_mxn
        plan_res = construir_plan(repartidor.posicion, sec_final or [], dist_f, dur_f, ingreso_estimado, evals_f, t0)
    else:
        items_act, carga_act = generar_items_paradas(plan_activo, None, t0)
        sec_act, dist_a, dur_a, evals_a, _ = resolver_secuencia_optima(
            repartidor.posicion, items_act, carga_act, capacidad_max=capacidad, clima=clima, t0=t0
        )
        plan_res = construir_plan(repartidor.posicion, sec_act or [], dist_a, dur_a, ingreso_plan_base, evals_a, t0)

    # Telemetría calculada
    entregados_aprox = max(0, int(repartidor.minutos_turno_transcurridos // 24))
    pedidos_totales = entregados_aprox + len(plan_activo) + len(ofertas_aceptadas)
    km_totales = max(repartidor.km_recorridos, 1.0)
    km_por_pedido = round(km_totales / max(1, pedidos_totales), 1)
    agrupamiento = round(1.0 + (len(plan_activo) + len(ofertas_aceptadas)) * 0.35, 1)

    telemetria = Telemetria(
        rho_actual_mxn_h=round(repartidor.rho_actual_mxn_h, 1),
        ganancia_turno_mxn=round(repartidor.ganancia_turno_mxn, 2),
        pedidos_entregados=entregados_aprox,
        puntualidad=0.94,
        km_por_pedido=km_por_pedido,
        factor_agrupamiento=agrupamiento,
        utilizacion=0.72,
    )

    # Alertas operativas si la frescura es baja
    for p in plan_res.paradas:
        if p.holgura_frescura_min is not None and p.holgura_frescura_min < 5.0:
            alertas.append(
                Alerta(
                    nivel="aviso",
                    codigo="frescura_critica",
                    pedido_id=p.pedido_id,
                    mensaje=f"Quedan {p.holgura_frescura_min:.1f} min de margen de frescura en el pedido {p.pedido_id[:6]}."
                )
            )

    return politica_efectiva, decisiones, plan_res, telemetria, alertas
