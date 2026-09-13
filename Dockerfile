FROM python:3.11-slim

WORKDIR /app

# Herramientas mínimas de sistema (curl para healthcheck, build-essential si es necesario)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python (Numba, NumPy, FastAPI, etc. sin PyTorch)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente del backend y algoritmos de IA
COPY . .

# Variables de entorno por defecto y optimización de Numba
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV NUMBA_CACHE_DIR=/tmp/numba_cache

# Pre-calentar el JIT de Numba y el grafo vial durante el build para evitar latencia en la primera petición
RUN python -c "from app.ai.sequencer import _warmup_numba; _warmup_numba(); from app.core.router import obtener_grafo_routing; obtener_grafo_routing(); print('JIT and Graph pre-warmed successfully')"

EXPOSE 8000

# Comando de ejecución con soporte para el puerto dinámico de Render/Cloud
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
