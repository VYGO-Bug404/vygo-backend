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

    # Política deseada: prioridad query param > body > agente_ppo por defecto
    politica_solicitada: Politica = politica or peticion.politica or "agente_ppo"

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
        version="1.0",
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
    politica: Optional[Politica] = Query(default="PPO", description="Política a evaluar: PPO o HIBRIDO"),
    persistir: bool = Query(default=True, description="Persistir decisiones en la base de datos (§5.3)"),
    reset_db: bool = Query(default=False, description="Reiniciar datos semilla antes de simular"),
):
    """
    Simulación end-to-end completa desde la base de datos Supabase:
      1. Extrae el estado ejecutando las 4 consultas SQL oficiales (§4.1).
      2. Evalúa las ofertas entrantes con la política seleccionada (PPO o HIBRIDO).
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
            politica=str(politica or "PPO"),
        )
    except Exception as ex:
        raise HTTPException(status_code=404, detail=str(ex))

    # 2. Ejecutar evaluador de políticas con optimización exacta Held-Karp
    pol_solicitada = politica or "PPO"
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
        viaje_id = peticion.plan_activo[0].pedido_id if peticion.plan_activo else "viaje-demo-01"
        rep_st = db.obtener_estado_repartidor(repartidor_id)
        if rep_st and rep_st.get("viaje_id"):
            viaje_id = rep_st["viaje_id"]

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
