# Acta de prueba funcional integrada — SIDI

**Identificador:** SIDI-PF-001  
**Fecha de ejecución y evidencias:** 6 de noviembre de 2026  
**Entorno:** Docker Desktop en Windows, PostgreSQL 16, RabbitMQ 3, NestJS, Python/IA, FastAPI y Angular 22  
**Alcance:** prueba de extremo a extremo del prototipo con mediciones **100 % sintéticas**  
**Estado:** *aprobada para los recorridos observados*, con limitaciones indicadas abajo  
**Responsable de ejecución:** equipo del proyecto SIDI (prueba local aportada mediante capturas y documentos)  
**Fuente de información:** capturas de PowerShell, PostgreSQL, RabbitMQ, API HTTP y PDF impresos de los dos dashboards aportados el 6/11/2026.

> **Aviso de alcance:** esta acta documenta una ejecución concreta en el equipo de desarrollo. No prueba validación externa con datos reales de una EPS, eficacia en campo, fraude confirmado ni preparación para producción.

## 1. Objetivo y recorrido

Comprobar que el sistema reciba mediciones sintéticas por HTTP, las publique en RabbitMQ, las evalúe con el modelo desplegado, persista su resultado en PostgreSQL y permita visualizar los indicadores mediante FastAPI y Angular 22.

```text
api-eps-ingesta (NestJS, HTTP :5000)
  POST /api/v1/mediciones, simulación de 100 solicitudes (intervalo >= 1 s)
       |
       v
RabbitMQ / cola medicion.registrada
       |
       v
consumer-eps-ia (Python + modelo y escalador históricos)
       | consulta perfiles en public.cliente_features
       | guarda estado y predicción
       v
PostgreSQL / sidi_live.mediciones
       |
       v
api-eps-ia (FastAPI, GET /api/dashboard/*?fuente=flujo)
       |
       v
eps-front (Angular 22 + Nginx, :8088)
  Dashboards estratégico y operativo
```

La fuente `sidi_live` procede del flujo de eventos sintéticos; `sidi_demo` es una semilla estática e independiente. El modelo utilizado por el consumidor es el **artefacto de despliegue histórico**; esta prueba no sustituye ni valida externamente los resultados de SIDI-RUN-003.

## 2. Procedimiento ejecutado

1. Se desplegaron los contenedores del entorno local y se ejecutaron las tareas idempotentes de preparación de esquema `sidi_live` y perfiles sintéticos `C00000`–`C00099`.
2. Se puso en marcha el simulador de `api-eps-ingesta`, que realiza un lote configurado de 100 solicitudes HTTP a `POST /api/v1/mediciones`, separadas por al menos un segundo.
3. Se corroboró en la base que el primer lote produjo 100 registros con estado `EVALUADA`.
4. Se envió una medición adicional para el cliente `C00000` con consumo `45.5 m³`; NestJS respondió que la lectura fue aceptada y encolada.
5. El consumidor registró la evaluación de la medición individual, `clase=1`, con score `91.64 %` en el log de esa petición.
6. La consulta SQL consolidada mostró 101 eventos evaluados, desglosados por clase.
7. El endpoint de FastAPI y los documentos impresos de los dashboards reportaron los mismos totales.
8. Se comprobó mediante la consola de RabbitMQ la cola `medicion.registrada` sin mensajes listos ni no confirmados y con un consumidor asociado, en el instante de la captura.

## 3. Resultados observados

### 3.1 PostgreSQL (consulta SQL de evidencia)

```text
estado_proceso | codigo_prediccion | count
---------------+-------------------+------
EVALUADA       |                 0 |   46
EVALUADA       |                 1 |   55
(2 rows)
```

**Total evaluadas:** 101. **Predichas normales:** 46. **Predichas irregulares:** 55. Estos valores son salidas del clasificador y no etiquetas verificadas por inspección.

### 3.2 API de dashboards (fuente = flujo)

Respuesta observada en `GET /api/dashboard/resumen?fuente=flujo`:

| Campo | Valor observado |
|---|---:|
| `origen` | `postgresql:sidi_live` |
| `es_demo` | `true` |
| `mediciones_total` | 101 |
| `clientes_total` | 100 |
| `alertas_total` | 55 |
| `evaluadas_total` | 101 |
| `lecturas_estimadas` | 12 |
| `consumo_promedio_m3` | 29.68 |
| `tasa_alertas_pct` | 54.46 |
| `sin_perfil_total` | 0 |
| `errores_total` | 0 |
| `pendientes_total` | 0 |

La tasa de alertas se refiere a las predicciones de clase 1 del conjunto simulado, no a incidencia poblacional de irregularidades en una EPS. La captura de la respuesta JSON consigna una actualización del 6/11/2026.

### 3.3 RabbitMQ y consumidor

- Cola: `medicion.registrada`.
- Mensajes `Ready`: **0**.
- Mensajes `Unacked`: **0**.
- Consumidores asociados: **1**.
- El consumidor registró la evaluación del cliente `C00000` con `clase=1`, `score=91.64%` y un identificador de evento único.
- La cola vacía refleja el **instante observado**; no acredita por sí sola la ausencia permanente de errores ni el histórico de confirmaciones.

### 3.4 Dashboards Angular 22

**Operativo:** el PDF aportado contiene **6 páginas**. Muestra 101 lecturas, 55 alertas, tasa aproximada 54.5 %, promedio aproximado 29.7 m³, 101 evaluadas y 0 sin perfil, errores o pendientes. Presenta distribución por cuatro sectores y una tabla de 55 registros con identificadores, fechas, clientes y scores. En esa tabla se visualiza también la predicción individual del cliente `C00000` (aproximadamente 91.6 %).

**Estratégico:** el PDF aportado contiene **3 páginas**. Muestra 101 mediciones, 100 clientes distintos, 55 alertas, promedio 29.7 m³, 12 lecturas estimadas, estados de procesamiento y agrupaciones por sector. La procedencia indicada es `postgresql:sidi_live`.

Ambas pantallas exponen información coherente con el endpoint y la base. Los PDF son **instantáneas estáticas**: no demuestran visualmente el refresco automático durante la recepción continua de eventos.

## 4. Matriz de verificación

| ID | Control | Evidencia aportada | Resultado |
|---|---|---|---|
| PF-01 | Publicación HTTP desde NestJS | Respuesta «Aceptado» para medición individual y estado del simulador | Conforme |
| PF-02 | Consumo de cola RabbitMQ | 1 consumidor y cola con 0 listos / 0 sin confirmar | Conforme en la captura |
| PF-03 | Carga de perfiles sintéticos | Log de `seed-sidi-perfiles`: 100 perfiles disponibles | Conforme |
| PF-04 | Persistencia de 100 + 1 eventos | SQL `EVALUADA`: 46 clase 0 y 55 clase 1 | Conforme |
| PF-05 | Inferencia individual | Log `C00000`, clase 1, score 91.64 % | Conforme |
| PF-06 | API de consulta | JSON con 101 mediciones y 55 alertas | Conforme |
| PF-07 | Vista operativa | PDF de 6 páginas con totales y registros | Conforme |
| PF-08 | Vista estratégica | PDF de 3 páginas con indicadores coincidentes | Conforme |
| PF-09 | Actualización automática durante el lote | Las capturas son estáticas; no hay secuencia temporal registrada | **No verificada directamente** |
| PF-10 | Datos reales de EPS y validación externa | No se dispone de datos reales | **No ejecutada** |

## 5. Inventario de evidencias originales

Estos archivos fueron aportados en la conversación de revisión del 6/11/2026 y forman parte del expediente de trabajo. **No se incorporan como archivos binarios en este commit documental**:

| Fuente | Archivo o captura proporcionada | Contenido |
|---|---|---|
| Captura SQL | Resultado de `sidi_live.mediciones` | 46 normales + 55 irregulares |
| Captura HTTP | `GET /api/dashboard/resumen?fuente=flujo` | Contadores 101/55/100; cero errores y pendientes |
| Captura RabbitMQ | Overview y detalle de `medicion.registrada` | Ready 0, Unacked 0, Consumers 1 |
| Captura Docker Desktop | Servicios activos en entorno local | Backend, frontend, base de datos, broker y consumidor |
| PDF dashboard operativo | `operativo.pdf`, 6 páginas | Indicadores, sectores y listado de alertas |
| PDF dashboard estratégico | `estrategico.pdf`, 3 páginas | Indicadores, serie mensual y sectores |
| Capturas PowerShell | Simulador, consulta SQL y logs del consumidor | Ejecución del flujo completo |

Para un anexo formal autónomo de tesis, adjuntar las copias de los PDF/capturas al expediente o al repositorio documental con sus hashes. No se afirma que los binarios estén versionados aquí.

## 6. Reproducción y consulta

Ejecutar desde la raíz de `eps_ai` con los repositorios hermanos y contenedores en ejecución. Los siguientes comandos **consultan** datos existentes; no generan una nueva prueba:

```powershell
docker compose ps
docker exec rabbitmq_eps_broker rabbitmqctl list_queues name messages_ready messages_unacknowledged consumers

docker compose exec -T postgres-eps-db psql -U postgres -d eps_db -c "SELECT estado_proceso, codigo_prediccion, COUNT(*) FROM sidi_live.mediciones GROUP BY 1,2 ORDER BY 1,2;"

Invoke-RestMethod 'http://localhost:8088/api/dashboard/resumen?fuente=flujo' | Format-List
Invoke-RestMethod 'http://localhost:8088/api/dashboard/alertas?fuente=flujo' | ConvertTo-Json -Depth 5
```

Abrir `http://localhost:8088/operativo` y `http://localhost:8088/estrategico` y seleccionar **Flujo RabbitMQ / IA**. Una nueva simulación o medición incrementará los totales; por tanto, los 101/55 corresponden exclusivamente a la instantánea de esta prueba.

## 7. Incidencias anteriores y acciones correctivas verificadas

Antes de la prueba se observó un intento fallido del consumidor de conectar PostgreSQL con `localhost:5433` desde Docker; luego se verificó la configuración correcta `DB_HOST=postgres-eps-db`, `DB_PORT=5432`. También se vieron reinicios previos por errores de conexión AMQP; un arranque posterior mostró `Esperando eventos en medicion.registrada` y se registraron inferencias exitosas. Estas incidencias históricas no se omiten del registro y no constituyen errores activos de la instantánea aceptada.

## 8. Alcance académico y recomendaciones

- **Observación 3 (entrenamiento y reproducibilidad):** esta evidencia demuestra integración funcional del **artefacto de inferencia desplegado**, pero no sustituye las métricas de validación cruzada, dataset, código de entrenamiento y pruebas de robustez de `SIDI-RUN-003`.
- **Pruebas funcionales:** el flujo extremo a extremo sí aporta evidencia útil para el apartado de pruebas del sistema y para una eventual observación del jurado relacionada con funcionamiento.
- **Limitaciones:** no se comprobó autenticación real, rendimiento bajo carga elevada, tolerancia a desconexiones sostenidas, ni refresco automático a partir de una serie temporal de capturas.
- **Mejoras:** guardar secuencia de capturas o video durante los 100 eventos; generar reporte trazable por `lote_id`; aplicar cola de mensajes fallidos y política de reintentos; preparar exportación/impresión optimizada de dashboards.
- Ningún resultado respalda afirmar que 55 casos fueron fraudes reales, que la tasa del 54.46 % se da en una EPS, ni que los dashboards hayan sido utilizados en producción.

**Conclusión:** para la ejecución documentada, se verificó la cadena `NestJS → RabbitMQ → IA → PostgreSQL → FastAPI → Angular 22` mediante consistencia entre el resultado SQL, la respuesta de la API, los logs y ambos dashboards. Esta acta es una evidencia de *funcionamiento del prototipo con datos sintéticos*.
