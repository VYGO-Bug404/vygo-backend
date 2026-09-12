import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="Vygo Agent API",
    description="Motor analítico de optimización de rutas y decisiones para repartidores multiapp en Monterrey (HackMTY 2026)",
    version="1.0.0",
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
