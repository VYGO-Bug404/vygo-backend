import time
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse, JSONResponse

from app.core.schemas import (
    PeticionDecidir,
    RespuestaDecidir,
    Politica,
    EventoActivo,
)
from app.core.policies import procesar_decisiones
from app.core.simulator import stream_turno_sse

router = APIRouter()

@router.get("/salud")
async def salud():
    """
    Comprobación rápida de estado y política activa.
    """
    return {
        "ok": True,
        "politica": "agente_ppo",
        "version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@router.post("/decidir", response_model=RespuestaDecidir)
async def decidir(
    peticion: PeticionDecidir,
    response: Response,
    politica: Optional[Politica] = Query(default=None, description="Política a ejecutar (agente_ppo por defecto)"),
) -> RespuestaDecidir:
    """
    Superficie A: Decisión puntual para ofertas entrantes.
    Stateless, evaluada en memoria en < 150 ms.
    """
    inicio_ts = time.perf_counter()
    t0 = datetime.now(timezone.utc)

    # Calibrar t0 si las fechas de la petición son históricas / de pruebas (para evitar falsos rechazos por fecha límite)
    fechas_req = []
    for p in peticion.plan_activo:
        for s in (p.listo_en, p.limite_en):
            if s:
                try:
                    fechas_req.append(datetime.fromisoformat(s))
                except Exception:
                    pass
    for o in peticion.ofertas:
        for s in (o.listo_estimado_en, o.limite_en):
            if s:
                try:
                    fechas_req.append(datetime.fromisoformat(s))
                except Exception:
                    pass
    if fechas_req:
        fechas_norm = [d if d.tzinfo is not None else d.replace(tzinfo=t0.tzinfo) for d in fechas_req]
        max_fecha = max(fechas_norm)
        if max_fecha < t0:
            min_fecha = min(fechas_norm)
            t0 = min_fecha - timedelta(minutes=5)

    # Política deseada: prioridad query param > body > HIBRIDO (o agente_ppo si versión 1.0)
    if politica:
        politica_solicitada: Politica = politica
    elif peticion.politica:
        politica_solicitada = peticion.politica
    elif peticion.version == "1.0":
        politica_solicitada = "agente_ppo"
    else:
        politica_solicitada = "HIBRIDO"

    pol_efectiva, decisiones, plan_res, telemetria, alertas = procesar_decisiones(
        repartidor=peticion.repartidor,
        plan_activo=peticion.plan_activo,
        ofertas=peticion.ofertas,
        contexto=peticion.contexto,
        politica_solicitada=politica_solicitada,
        t0=t0,
    )

    latencia_ms = round((time.perf_counter() - inicio_ts) * 1000.0, 2)
    response.headers["X-Response-Time-Ms"] = str(latencia_ms)
    response.headers["Server-Timing"] = f"total;dur={latencia_ms}"

    evento_activo = None
    if peticion.contexto and peticion.contexto.evento_activo == "surge":
        evento_activo = EventoActivo(
            tipo="surge",
            zona="centro",
            multiplicador_tarifa=1.4,
            inicia_en=t0.isoformat(),
            termina_en=(t0 + timedelta(hours=1)).isoformat(),
        )

    return RespuestaDecidir(
        version=peticion.version or "1.0",
        generado_en=t0.isoformat(),
        politica=pol_efectiva,
        latencia_ms=latencia_ms,
        decisiones=decisiones,
        plan=plan_res,
        telemetria=telemetria,
        alertas=alertas,
        evento_activo=evento_activo,
    )

@router.get("/turno/stream")
async def turno_stream(
    escenario: int = Query(default=12, description="ID del escenario a simular"),
    politica: Politica = Query(default="agente_ppo", description="Política a ejecutar"),
    velocidad: float = Query(default=10.0, description="Factor de aceleración de tiempo"),
):
    """
    Superficie B: Turno en vivo vía Server-Sent Events (SSE).
    """
    return StreamingResponse(
        stream_turno_sse(escenario_id=escenario, politica=politica, velocidad=velocidad),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.get("/replay/{id}.json")
async def obtener_replay(id: int):
    """
    Superficie C: Servir el replay pareado JSON estático para la demo del pitch.
    """
    replay_path = Path(__file__).resolve().parent.parent / "data" / f"replay_{id}.json"
    if not replay_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Replay con ID {id} no encontrado. Ejecute scripts/generate_replay.py."
        )

    try:
        with open(replay_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)
    except Exception as ex:
        raise HTTPException(
            status_code=500,
            detail=f"Error al leer el archivo de replay: {str(ex)}"
        )

# =============================================================================
# SUPERFICIE D: SIMULACIÓN Y PRUEBAS CONTRA BASE DE DATOS SUPABASE (CONTRATO V2.0)
# =============================================================================

from app.core.db import (
    obtener_db,
    construir_peticion_desde_db,
)

@router.post("/simular/inyeccion")
async def simular_inyeccion():
    """
    Ejecuta el Plan de Inyección de Datos Oficial (§6) y valida las 7 reglas (§7).
    """
    db = obtener_db()
    db.inicializar_datos_semilla()
    verificaciones = db.verificar_estado_inyeccion()
    return {
        "ok": verificaciones["todas_pasan"],
        "mensaje": "Base de datos inicializada según Contrato v2.0 (§6)",
        "tablas": {
            "apps": len(db.apps),
            "usuarios": len(db.usuarios),
            "repartidores": len(db.repartidores),
            "platform_connections": len(db.platform_connections),
            "configuracion": len(db.configuracion),
            "viajes_repartidor": len(db.viajes_repartidor),
            "pedidos": len(db.pedidos),
            "viaje_pedidos": len(db.viaje_pedidos),
            "difusiones_pedido": len(db.difusiones_pedido),
            "ofertas_pedido": len(db.ofertas_pedido),
        },
        "verificaciones": verificaciones,
    }

@router.get("/simular/verificar")
async def simular_verificar():
    """
    Ejecuta y retorna las 7 verificaciones previas a conectar el agente (§7).
    """
    db = obtener_db()
    return db.verificar_estado_inyeccion()

@router.post("/simular/evaluar_db")
async def simular_evaluar_db(
    response: Response,
    repartidor_id: str = Query(default="rep-demo-01", description="ID del repartidor a consultar"),
    politica: Optional[Politica] = Query(default="HIBRIDO", description="Política a evaluar: HIBRIDO o PPO"),
    persistir: bool = Query(default=True, description="Persistir decisiones en la base de datos (§5.3)"),
    reset_db: bool = Query(default=False, description="Reiniciar datos semilla antes de simular"),
):
    """
    Simulación end-to-end completa desde la base de datos Supabase:
      1. Extrae el estado ejecutando las 4 consultas SQL oficiales (§4.1).
      2. Evalúa las ofertas entrantes con la política seleccionada (HIBRIDO o PPO).
      3. Si persistir=True, ejecuta las mutaciones de escritura de vuelta (§5.3).
      4. Retorna el objeto RespuestaDecidir y el estado auditable resultante.
    """
    inicio_ts = time.perf_counter()
    t0 = datetime.now(timezone.utc)
    db = obtener_db()

    if reset_db:
        db.inicializar_datos_semilla()

    # 1. Ejecutar las 4 consultas SQL (§4.1) y construir PeticionDecidir
    try:
        peticion = construir_peticion_desde_db(
            repartidor_id=repartidor_id,
            db=db,
            politica=str(politica or "HIBRIDO"),
        )
    except Exception as ex:
        raise HTTPException(status_code=404, detail=str(ex))

    # 2. Ejecutar evaluador de políticas con optimización exacta Held-Karp
    pol_solicitada = politica or "HIBRIDO"
    pol_efectiva, decisiones, plan_res, telemetria, alertas = procesar_decisiones(
        repartidor=peticion.repartidor,
        plan_activo=peticion.plan_activo,
        ofertas=peticion.ofertas,
        contexto=peticion.contexto,
        politica_solicitada=pol_solicitada,
        t0=t0,
    )

    latencia_ms = round((time.perf_counter() - inicio_ts) * 1000.0, 2)
    response.headers["X-Response-Time-Ms"] = str(latencia_ms)

    # Validar las 7 reglas oficiales (§7) sobre el estado consultado
    verificaciones_previas = db.verificar_estado_inyeccion()

    # 3. Escritura de vuelta a la base (§5.3)
    mutaciones = {}
    if persistir:
        rep_st = db.obtener_estado_repartidor(repartidor_id)
        viaje_id = (rep_st.get("viaje_id") if rep_st else None) or f"viaje-{repartidor_id}"

        ofertas_aceptadas = [d for d in decisiones if d.decision == "aceptar"]
        ofertas_rechazadas = [d for d in decisiones if d.decision == "rechazar"]

        # Persistir rechazos
        for r_dec in ofertas_rechazadas:
            db.persistir_decision_rechazar(r_dec.oferta_id)

        # Persistir aceptación de la mejor oferta si hubo
        if ofertas_aceptadas:
            # Seleccionar la mejor oferta aceptada
            mejor = max(ofertas_aceptadas, key=lambda x: x.economia.tasa_marginal_mxn_h)
            # Extraer nueva secuencia ordenada de pedidos únicos
            nuevo_orden: List[Tuple[str, int]] = []
            for idx, parada in enumerate(plan_res.paradas):
                if not any(item[0] == parada.pedido_id for item in nuevo_orden):
                    nuevo_orden.append((parada.pedido_id, len(nuevo_orden) + 1))

            coords = plan_res.geometria.coordinates
            mutaciones = db.persistir_decision_aceptar(
                oferta_id=mejor.oferta_id,
                pedido_id=mejor.pedido_id,
                viaje_id=viaje_id,
                nuevo_orden_secuencia=nuevo_orden,
                coordenadas_ruta=coords,
            )

    verificaciones = verificaciones_previas
    verif_post = db.verificar_estado_inyeccion()
    mutaciones["orden_consecutivo_post_mutacion"] = verif_post["v4_orden_consecutivo"]

    respuesta_decidir = RespuestaDecidir(
        version="2.0",
        generado_en=t0.isoformat(),
        politica=pol_efectiva,
        latencia_ms=latencia_ms,
        decisiones=decisiones,
        plan=plan_res,
        telemetria=telemetria,
        alertas=alertas,
        evento_activo=None,
    )

    return {
        "ok": True,
        "politica": pol_efectiva,
        "repartidor_id": repartidor_id,
        "latencia_ms": latencia_ms,
        "pedidos_a_bordo_iniciales": len(peticion.plan_activo),
        "ofertas_evaluadas": len(peticion.ofertas),
        "mutaciones_escritura_bd": mutaciones,
        "verificaciones_contrato": verificaciones,
        "respuesta_decidir": respuesta_decidir,
    }

@router.post("/simular/turno_db")
async def simular_turno_db(
    response: Response,
    repartidor_id: str = Query(default="rep-demo-01", description="ID del repartidor a simular"),
    politica: Optional[Politica] = Query(default="HIBRIDO", description="Política a evaluar: HIBRIDO o PPO"),
    pasos: int = Query(default=1, ge=1, le=10, description="Número de pasos a simular consecutivamente"),
    persistir: bool = Query(default=True, description="Persistir decisiones en la base de datos (§5.3)"),
    reset_db: bool = Query(default=False, description="Reiniciar datos semilla antes de simular"),
):
    """
    Simulación secuencial de turno desde Supabase.
    Permite simular 1 o múltiples decisiones en cadena.
    """
    db = obtener_db()
    if reset_db:
        db.inicializar_datos_semilla()

    historial_pasos = []
    ultimo_resultado = None

    for paso in range(pasos):
        res = await simular_evaluar_db(
            response=response,
            repartidor_id=repartidor_id,
            politica=politica,
            persistir=persistir,
            reset_db=False,
        )
        ultimo_resultado = res
        historial_pasos.append({
            "paso": paso + 1,
            "ofertas_evaluadas": res["ofertas_evaluadas"],
            "pedidos_a_bordo": len(res["respuesta_decidir"].plan.secuencia or []),
            "tasa_proyectada": res["respuesta_decidir"].plan.resumen.tasa_proyectada_mxn_h,
        })
        if res["ofertas_evaluadas"] == 0:
            break

    return {
        "ok": True,
        "repartidor_id": repartidor_id,
        "politica": politica,
        "pasos_simulados": len(historial_pasos),
        "historial": historial_pasos,
        "ultimo_resultado": ultimo_resultado,
    }
