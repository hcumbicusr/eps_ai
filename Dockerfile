# SIDI - servicios FastAPI/consumidor Python (no incluye frontend Angular)
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev python3-dev git python3-pkg-resources \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "setuptools<82.0.0" "pip<25.3" wheel
COPY requirements.txt .
RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt --default-timeout=100
COPY models/ ./models/
COPY src/ ./src/
COPY scripts/ ./scripts/
RUN mkdir -p data
EXPOSE 8000
