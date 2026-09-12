FROM python:3.11-slim

WORKDIR /app

# Herramientas mínimas de sistema
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Variables de entorno por defecto
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Comando de ejecución con soporte para el puerto dinámico de Render/Cloud
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
