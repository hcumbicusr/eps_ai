# Módulo SIDI Dashboard — eps_ai/training

Módulo HTTP **exclusivamente de lectura** para la app Angular 22 [`eps-front`](https://github.com/hcumbicusr/eps-front). Se incorpora a FastAPI, sin modificar los endpoints de inferencia ni los scripts/modelos de entrenamiento.

## Arquitectura

- `src/dashboard/router.py`: expone `/api/dashboard/resumen`, `/api/dashboard/detalle`, `/api/dashboard/alertas`.
- `src/dashboard/service.py`: consulta únicamente `sidi_demo.mediciones` y `sidi_demo.alertas`, con parámetros SQL enlazados.
- `src/dashboard/models.py`: contratos Pydantic correspondientes al frontend.
- `scripts/dashboard/seed_sidi_demo.sql`: 5 984 mediciones y 9 alertas **ficticias**, 1 200 clientes, fechas de 2025. `ON CONFLICT DO NOTHING`; no sobrescribe datos existentes.
- `scripts/dashboard/seed_demo.py`: ejecuta la semilla manualmente desde Python.
- `tests/test_dashboard_*.py`: tests de contrato e integración PostgreSQL.

La carga NO altera `feature_store_lecturas`, `cliente_features` ni `alertas_irregularidades`. Los nombres de sectores son inventados y la tasa de alertas se calcula solo sobre las tablas demo.

## Requisitos de carpetas

```text
proyecto-sidi/
├── eps_ai/              # ejecutar Docker Compose desde aquí
├── eps-front/           # Dockerfile y Angular 22
└── api-eps-ingesta/     # NestJS independiente
```

## Arranque integrado

Desde `eps_ai`, con `.env` local configurado y repositorios hermanos clonados:

```bash
docker compose up -d --build
# El servicio seed-sidi-demo crea (si no existe) el esquema sidi_demo
docker compose logs --tail=80 seed-sidi-demo
docker compose logs --tail=80 api-eps-ia
```

- Frontend: http://localhost:8088
- API: http://localhost:8000/api/dashboard/resumen
- Documentación Swagger: http://localhost:8000/docs
- PostgreSQL: `localhost:5433` desde host, `postgres-eps-db:5432` en Docker.

**Importante:** este despliegue usa la base persistente del stack actual. No borra datos históricos. La carga es idempotente. Si cambias la semilla en una ejecución futura, `ON CONFLICT DO NOTHING` conservará filas existentes; gestiona migraciones explícitamente.

## Verificación SQL

```sql
SELECT count(*) FROM sidi_demo.mediciones;  -- 5984
SELECT count(*) FROM sidi_demo.alertas;     -- 9
```

Con credenciales de desarrollo, la API y frontend deben permanecer accesibles solo en un entorno de pruebas de confianza: no hay autenticación real.
