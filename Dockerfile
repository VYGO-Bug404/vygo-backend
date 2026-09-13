FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
ENV PYTHONUNBUFFERED=1
# Cache en directorio persistente dentro del contenedor (no /tmp que es efímero)
ENV NUMBA_CACHE_DIR=/app/.numba_cache

# Pre-calentar el grafo vial durante el build para evitar cold-start en la primera petición.
# El || true evita que una falla de memoria o de red aborte el build — el startup de FastAPI
# también precalienta el grafo como respaldo.
RUN python -c "\
try:\n\
    from app.core.router import obtener_grafo_routing; obtener_grafo_routing(); print('[Docker build] Grafo vial precalentado.')\n\
except Exception as e:\n\
    print(f'[Docker build] Precalentamiento omitido: {e} — se precalentará en startup.')\n\
" || true

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
