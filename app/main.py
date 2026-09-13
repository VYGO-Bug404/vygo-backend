import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

logger = logging.getLogger("vygo.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Precalentar el grafo vial A* al iniciar el servidor (importante en Docker
    # para que la primera petición /ruteo no tenga cold-start de 5-10 s)
    try:
        from app.core.router import obtener_grafo_routing
        G = obtener_grafo_routing()
        if G is not None:
            logger.info(f"[startup] Grafo vial listo: {len(G.nodes)} nodos, {len(G.edges)} aristas")
        else:
            logger.warning("[startup] Grafo vial no disponible — ruteo usará interpolación de respaldo")
    except Exception as e:
        logger.warning(f"[startup] Error precalentando grafo: {e}")
    yield


app = FastAPI(
    title="Vygo Agent API",
    description="Motor analítico de optimización de rutas y decisiones para repartidores multiapp en Monterrey (HackMTY 2026)",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware CORS permisivo para permitir frontend en React desplegado en Vercel o localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Response-Time-Ms", "X-Process-Time-Ms", "Server-Timing"],
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    inicio = time.perf_counter()
    response = await call_next(request)
    duracion_ms = round((time.perf_counter() - inicio) * 1000.0, 2)
    response.headers["X-Process-Time-Ms"] = str(duracion_ms)
    return response

# Incluir rutas principales
app.include_router(router)

@app.get("/")
async def root():
    return {
        "sistema": "Vygo Courier AI Engine",
        "reto": "HackMTY 2026 - The Courier",
        "version": "1.0",
        "documentacion": "/docs",
        "salud": "/salud",
    }
