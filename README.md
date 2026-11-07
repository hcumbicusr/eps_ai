# SIDI — Sistema Inteligente de Detección de Irregularidades

**Repositorio:** [`hcumbicusr/eps_ai`](https://github.com/hcumbicusr/eps_ai) · **rama de integración:** `training`.

SIDI es un prototipo de investigación aplicada para la **detección preliminar de patrones irregulares en consumos de agua potable**. La implementación integra ingesta HTTP de lecturas, RabbitMQ, un consumidor Python con un clasificador de IA, PostgreSQL, una API FastAPI y dos dashboards Angular 22. **Los datasets y las lecturas del simulador son sintéticos; no se ha realizado validación con registros reales de una EPS.** Las predicciones no constituyen comprobaciones de fraude.

## 1. Repositorios y responsabilidades

| Proyecto | Repositorio / rama | Responsabilidad |
|---|---|---|
| Backend, IA y despliegue | [`eps_ai/training`](https://github.com/hcumbicusr/eps_ai/tree/training) | Entrenamiento, artefactos de inferencia, consumidor RabbitMQ, FastAPI, esquemas PostgreSQL y `docker-compose.yml` orquestador |
| API de ingesta | [`api-eps-ingesta/main`](https://github.com/hcumbicusr/api-eps-ingesta) | NestJS: `POST /api/v1/mediciones`, simulador de 100 solicitudes y publicación de eventos |
| Frontend | [`eps-front/main`](https://github.com/hcumbicusr/eps-front) | Angular 22: login demostrativo, dashboard estratégico y operativo, servido por Nginx |

Los tres repositorios deben estar **al mismo nivel**, no anidados:

```text
proyecto-sidi/
├── eps_ai/              # rama training; aquí se ejecuta docker compose
├── api-eps-ingesta/      # rama main
└── eps-front/            # rama main
```

## 2. Arquitectura integrada

```text
                        SIMULADOR DE MEDICIONES / CLIENTE HTTP
                                      |
                       100 POST, 1 cada >= 1 s
                                      v
          api-eps-ingesta (NestJS, puerto 5000)
                 POST /api/v1/mediciones
                       | evento_id / lote_id
                       v
              RabbitMQ: medicion.registrada
                       |
                       v
               consumer-eps-ia (Python)
                       |
           +-----------+------------+
           |                        |
    public.cliente_features     models/*.pkl
    (perfiles sintéticos)       (modelo y scaler legado)
           |                        |
           +------------+-----------+
                        |
                        v
                PostgreSQL eps_db
                sidi_live.mediciones
          (todas las recibidas + estado + score)
                        |
           +------------+------------+
           |                         |
     sidi_live.*                 sidi_demo.*
     (flujo de IA)               (datos semilla)
           |                         |
           +------------+------------+
                        v
             api-eps-ia (FastAPI :8000)
       GET /api/dashboard/*?fuente=flujo|demo
                        |
                     HTTP /api/*
                        v
             Nginx + eps-front Angular 22
                    localhost:8088
```

El endpoint `POST /predict` de FastAPI continúa disponible para evaluaciones puntuales, **separado de la ingesta NestJS y del consumo RabbitMQ**. Los dashboards consultan PostgreSQL únicamente a través de FastAPI; ninguna contraseña de BD se envía a Angular.

### Separación de los datos

- **`feature_store_lecturas`**: datos de entrenamiento sintéticos cargados desde CSV (flujo histórico).
- **`cliente_features`**: perfiles necesarios para crear el vector de 22 variables antes de cada inferencia.
- **`sidi_demo.mediciones` y `sidi_demo.alertas`**: semilla fija de 5.984 mediciones, 1.200 clientes y 9 alertas ficticias; no cambia al ejecutar el simulador.
- **`sidi_live.mediciones`**: eventos llegados por RabbitMQ. Se guarda la recepción, su evaluación (normal o alerta) o `SIN_PERFIL`/`ERROR`, incluyendo marca temporal, lote, cliente y puntuación cuando existe. La tabla permanece después de reiniciar los contenedores.
- **`alertas_irregularidades`**: tabla histórica de alertas del consumidor anterior. El nuevo dashboard de flujo usa exclusivamente `sidi_live.mediciones`; no suma sus filas a las de otros esquemas.

La predicción utiliza el **modelo híbrido y el escalador serializados en `models/`**. Los experimentos auditados `SIDI-RUN-003` y `SIDI-STRESS-001` son evidencias reproducibles separadas, **no el modelo instalado automáticamente en el consumidor**.

## 3. Requisitos y configuración

- Docker Desktop + Docker Compose para ejecutar toda la solución.
- Git; se recomienda disponer de puertos libres `5433`, `5672`, `15672`, `5000`, `8000` y `8088`.
- Para ejecución Python fuera de Docker: Python 3.11 y dependencias de `requirements.txt`. Para Angular, utilizar la versión Node exigida en `eps-front/package.json`.

Desde `eps_ai`:

```powershell
# Cree .env solo si aún no existe; no sobreescriba su configuración actual.
Copy-Item .env-example .env
```

Variables importantes:

| Variable | Uso / entorno |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Creación y acceso a PostgreSQL |
| `DB_USER`, `DB_PASS`, `DB_NAME` | Credenciales de las aplicaciones Python |
| `DB_HOST`, `DB_PORT` | En el host: `localhost:5433`; los contenedores Python usan `postgres-eps-db:5432` por Compose |
| `RABBIT_USER`, `RABBIT_PASS`, `RABBIT_HOST`, `RABBIT_PORT` | Mensajería RabbitMQ |
| `QUEUE_NAME_MEDICION_REGISTRADA` | Cola `medicion.registrada` |
| `IA_PORT`, `INGESTA_PORT`, `FRONT_PORT` | Puertos externos FastAPI, NestJS y frontend (frontend por defecto `8088`) |
| `SIMULATOR_ENABLED` | `true` habilita simulador **solo en desarrollo** |
| `SIMULATOR_TOKEN` | Token local para iniciar y consultar simulaciones |
| `TRAINING_DATASET_FILE` | CSV sintético utilizado en las cargas históricas y perfiles de prueba |

Use credenciales propias del entorno local y no exponga estos servicios a Internet sin autenticación, TLS, permisos de base de datos y gestión de secretos.

## 4. Despliegue completo con Docker

```powershell
cd D:\Personal\git\eps_ai
# Asegúrese de actualizar los repositorios hermanos en sus ramas indicadas.
# En eps_ai: git pull origin training
# En api-eps-ingesta y eps-front: git pull origin main

docker compose up -d --build

docker compose ps
```

Los trabajos `seed-sidi-demo`, `init-sidi-live` y `seed-sidi-perfiles` **terminan con código 0** después de completar su tarea: que aparezcan como `Exited` no es un fallo. La primera carga puede tardar mientras se construyen las imágenes. El volumen `eps_postgres_data` conserva PostgreSQL entre reinicios.

Servicios y accesos:

| Servicio Compose | Dirección host | Función |
|---|---|---|
| `postgres-eps-db` | `localhost:5433` | PostgreSQL 16 |
| `rabbitmq-eps-broker` | `localhost:5672` / `http://localhost:15672` | Cola y consola RabbitMQ |
| `api-eps-ingesta` | `http://localhost:5000` | Recepción y simulación de mediciones |
| `consumer-eps-ia` | Sin puerto | Cálculo de inferencias y persistencia |
| `api-eps-ia` | `http://localhost:8000/docs` | FastAPI e indicadores |
| `eps-front` | `http://localhost:8088/login` | Angular 22 |

**Cargas iniciales idempotentes**:

- `seed-sidi-demo` preserva los 5.984 y 9 registros estáticos si ya existen.
- `init-sidi-live` crea `sidi_live.mediciones` y sus índices mediante `IF NOT EXISTS`, sin borrar registros.
- `seed-sidi-perfiles` lee los 100 clientes `C00000` a `C00099` del CSV sintético y los añade con `ON CONFLICT DO NOTHING`; **no trunca** `cliente_features` ni altera perfiles previos.

Para revisar las cargas:

```powershell
docker compose logs --tail=60 seed-sidi-demo
docker compose logs --tail=60 init-sidi-live
docker compose logs --tail=60 seed-sidi-perfiles
```

## 5. Simulación de 100 mediciones

La API NestJS (`api-eps-ingesta/main`) dispone de:

- `POST /api/v1/mediciones` — recibe una medición, añade `evento_id` y publica `medicion.registrada`.
- `POST /api/v1/mediciones/simulaciones` — inicia 100 peticiones HTTP separadas al menos un segundo, en segundo plano.
- `GET /api/v1/mediciones/simulaciones/{id}` — consulta el progreso del lote, con contadores HTTP.

Configure en `eps_ai/.env`:

```dotenv
SIMULATOR_ENABLED=true
SIMULATOR_TOKEN=un-token-local-para-pruebas
```

Después de actualizar `api-eps-ingesta/main`, reconstruya su contenedor si es necesario:

```powershell
docker compose up -d --build --force-recreate api-eps-ingesta consumer-eps-ia
```

Lanzar y consultar el trabajo desde PowerShell:

```powershell
$headers = @{ 'x-sidi-simulator-token' = 'un-token-local-para-pruebas' }
$job = Invoke-RestMethod -Method Post -Uri 'http://localhost:5000/api/v1/mediciones/simulaciones' -Headers $headers
$job | Format-List
Invoke-RestMethod -Method Get -Uri "http://localhost:5000/api/v1/mediciones/simulaciones/$($job.id)" -Headers $headers | Format-List
```

`aceptadas_http=100` **no significa** que la IA evaluó 100 mediciones. Compruebe separadamente las filas con `estado_proceso='EVALUADA'` y los estados `SIN_PERFIL`, `RECIBIDA` y `ERROR`.

Los eventos nuevos incluyen `evento_id` para evitar duplicados al reentregar un mensaje y `lote_id` para identificar la simulación. Mensajes antiguos sin identificador reciben un UUID generado por el consumidor (no tienen deduplicación garantizada frente a reentregas).

## 6. Dashboards Angular 22: demo vs. flujo

- **Flujo RabbitMQ/IA (predeterminado):** `GET /api/dashboard/resumen?fuente=flujo`, `detalle` y `alertas`. Los valores aumentan a medida que llegan mensajes al consumidor; el frontend consulta la API automáticamente cada 5 segundos. Esta fuente **puede comenzar en cero**.
- **Semilla demo:** `?fuente=demo` muestra el escenario precargado de 5.984 mediciones y 9 alertas, independiente de los nuevos eventos. El selector de fuente está en el encabezado de Angular.

Endpoints y ejemplos:

```powershell
Invoke-RestMethod 'http://localhost:8088/api/dashboard/resumen?fuente=flujo' | Format-List
Invoke-RestMethod 'http://localhost:8088/api/dashboard/resumen?fuente=demo' | Format-List
Invoke-RestMethod 'http://localhost:8088/api/dashboard/detalle?fuente=flujo' | ConvertTo-Json -Depth 5
Invoke-RestMethod 'http://localhost:8088/api/dashboard/alertas?fuente=flujo' | ConvertTo-Json -Depth 5
```

**Qué significa cada contador del flujo:** `mediciones_total` es el número de eventos registrados; `evaluadas_total` cuenta inferencias efectivamente calculadas; `alertas_total` cuenta predicciones de clase 1 (no fraude confirmado); `sin_perfil_total` eventos sin perfil en `cliente_features`; `errores_total` eventos con error registrado; `pendientes_total` recepciones sin finalizar. La tasa de alertas se calcula como `alertas_total / evaluadas_total` (no sobre HTTP aceptadas).

El selector de sector y estado filtra la tabla de alertas según PostgreSQL. Las mediciones, series y alertas se actualizan en ambos dashboards sin recargar la página completa.

## 7. Consultas SQL de verificación

```powershell
# Verificar contadores del flujo y estado de procesamiento.
docker compose exec -T postgres-eps-db psql -U postgres -d eps_db -c "SELECT estado_proceso, count(*) FROM sidi_live.mediciones GROUP BY 1 ORDER BY 1;"

# Contar alertas de IA y eventos por lote.
docker compose exec -T postgres-eps-db psql -U postgres -d eps_db -c "SELECT lote_id, count(*) AS recibidas, count(*) FILTER (WHERE estado_proceso='EVALUADA') AS evaluadas, count(*) FILTER (WHERE codigo_prediccion=1) AS alertas FROM sidi_live.mediciones GROUP BY lote_id ORDER BY recibidas DESC;"

# Confirmar que la carga fija no cambia.
docker compose exec -T postgres-eps-db psql -U postgres -d eps_db -c "SELECT count(*) FROM sidi_demo.mediciones;"
```

Cambie `postgres` y `eps_db` en los ejemplos si utiliza otros valores de `POSTGRES_USER` y `POSTGRES_DB`.

## 8. Diagnóstico de eventos y Docker

```powershell
docker compose ps
docker compose logs --tail=120 api-eps-ingesta
docker compose logs --tail=120 consumer-eps-ia
docker compose logs --tail=100 api-eps-ia
docker compose logs --tail=60 eps-front
docker exec rabbitmq_eps_broker rabbitmqctl list_queues name messages_ready messages_unacknowledged consumers
```

- **HTTP aceptadas, flujo sin filas:** revise que NestJS publique el evento y que `consumer-eps-ia` esté conectado a RabbitMQ y PostgreSQL; compruebe errores en logs.
- **`SIN_PERFIL`:** confirme que `seed-sidi-perfiles` terminó correctamente y que `cliente_features` tiene los clientes simulados.
- **`RECIBIDA`:** el evento aún no terminó o el consumidor se interrumpió durante el proceso.
- **`ERROR`:** consulte `detalle_error`, controle calidad de variables y versión de modelo/escalador.
- **RabbitMQ con CPU alta:** el consumidor espacia los reintentos de fallos de infraestructura 2 segundos para reducir ciclos intensivos. Se recomienda una futura cola de mensajes fallidos y una política explícita de reintentos.
- **Nuevo frontend no refleja cambios:** `git pull` en `eps-front/main` y `docker compose up -d --build eps-front`; el navegador debe abrir `localhost:8088`.
- **Almacenamiento:** no ejecute `docker compose down -v` si desea conservar los datos del volumen PostgreSQL.

## 9. Código, entrenamiento y evidencia experimental

```text
data/                              Dataset sintético 96.000 × 27
models/                            Modelo y escalador históricos desplegados
src/1_data_ingestion.py             CSV → feature_store_lecturas (histórico)
src/2_model_preprocessing.py        Preparación histórica del modelo
src/3_model_training.py             Entrenamiento histórico de cuatro modelos
src/4_fastapi_service.py           Predicción REST y registro del router de dashboards
src/5_model_consumer.py            Consumidor RabbitMQ, inferencia y sidi_live
src/config.py                      Configuración de datos, IA y mensajería
src/dashboard/                     Modelos, API, consultas demo/live y persistencia
src/experiments/                   Entrenamiento reproducible SIDI-RUN-003
scripts/dashboard/                 Semillas demo, esquema live, perfiles para simulación
tests/                             Pruebas de contratos y PostgreSQL
protocolos/                        Configuración experimental y manifiestos
evidencias/observacion_3/          Auditoría, folds, robustez y anexos de evidencia
docker-compose.yml                 Orquestación de los tres repositorios
```

El generador del dataset sintético puede ejecutarse con `python -m src.utils.generate_dataset`. Los scripts históricos usan PostgreSQL y, en algunos casos, **sobrescriben tablas** (`1_data_ingestion.py` usa `if_exists='replace'`; `populate_features.py` usa `TRUNCATE`). No ejecute esos scripts sobre tablas cuya información desee conservar.

`SIDI-RUN-003`: partición estratificada 80/20, cinco folds y evaluación final de los cuatro modelos, con Soft Voting seleccionado por mayor F1. `SIDI-STRESS-001`: evaluación de robustez en cinco escenarios sintéticos. Las evidencias y el protocolo externo futuro están en [`evidencias/observacion_3`](evidencias/observacion_3/README.md). **No existe validación externa ejecutada con datos reales de EPS.**

## 10. Limitaciones y seguridad

- Este despliegue es de demostración. El acceso del login de Angular es visual y **no autentica usuarios**. Los endpoints de dashboards y `/predict` carecen de autorización. Ejecutarlos únicamente en redes controladas.
- Las credenciales de Docker son de laboratorio: no reutilizarlas en sistemas públicos ni productivos.
- Las predicciones de la IA son alertas preliminares: el sistema no verifica fraudes ni reemplaza inspección especializada.
- `api-eps-ingesta` mantiene el historial de simulaciones en memoria; reiniciar NestJS borra esos estados HTTP, aunque los eventos ya persistidos permanecen en PostgreSQL.
- Para producción faltan control de acceso, migraciones gestionadas, contratos de eventos versionados, colas de mensajes fallidos, observabilidad, control de retención y validación con datos EPS reales.
- Los dashboards consultan datos de una fuente seleccionada, nunca suman las cifras de `sidi_demo` y `sidi_live`.

---

## 11. Acta de prueba funcional integrada — 6 de noviembre de 2026

La prueba local documentada con **mediciones sintéticas** confirmó el procesamiento y la persistencia de **101 lecturas** (100 del simulador y una medición adicional). PostgreSQL registró **46 predicciones normales y 55 predicciones de clase irregular**, sin eventos sin perfil, pendientes ni errores en la instantánea revisada. La API FastAPI y ambos dashboards Angular 22 mostraron contadores concordantes. RabbitMQ indicó 0 mensajes listos, 0 sin confirmar y un consumidor activo en el momento de la captura.

- **[Acta de prueba funcional integrada — SIDI-PF-001](docs/PRUEBA_INTEGRACION_SIDI.md)**: alcance, procedimiento, matriz de verificación, resultados, incidencias previas, limitaciones y relación con las observaciones de tesis.
- **[Consultas SQL reproducibles](docs/CONSULTAS_PRUEBA_INTEGRACION_SIDI.sql)**: verificación de estados, clases, lotes y separación entre `sidi_demo` y `sidi_live`.

Los PDF originales `operativo.pdf` (6 páginas) y `estrategico.pdf` (3 páginas), junto con capturas de SQL, API, RabbitMQ y Docker, fueron aportados por el equipo en la conversación del 6/11/2026; **no están añadidos como binarios en el repositorio**. Los conteos 101/55 son una instantánea, no una meta fija ni evidencia de validación con datos reales de una EPS.
