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
