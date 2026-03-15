# 1. Imagen base
FROM python:3.11-slim

# 2. Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# 3. Dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev python3-dev git python3-pkg-resources \
    && rm -rf /var/lib/apt/lists/*

# 4. Forzar herramientas compatibles
RUN pip install --no-cache-dir "setuptools<82.0.0" "pip<25.3" wheel

# 5. Instalación de dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt --default-timeout=100

# 6. Copiar el Modelo de IA y el Código Fuente
COPY models/ ./models/
COPY src/ ./src/
RUN mkdir data

EXPOSE 8000
