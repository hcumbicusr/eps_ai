# SIDI – Informe de auditoría técnica y metodológica (Paso 1)

**Proyecto:** Sistema Inteligente de Detección de Irregularidades (SIDI) para empresas prestadoras de servicios de saneamiento (EPS) en Perú  
**Propósito:** preparar evidencia verificable para responder a la **observación 3** del jurado (dataset y generador, código/versiones, experimentos y resultados por fold, matrices y protocolo de validación externa).  
**Fecha de corte:** 4 de noviembre de 2026  
**Repositorio:** https://github.com/hcumbicusr/eps_ai/tree/training  
**Commit auditado (`training`):** [`d2cdc2dc120bbb9aef643ac9e6035f179170fc92`](https://github.com/hcumbicusr/eps_ai/commit/d2cdc2dc120bbb9aef643ac9e6035f179170fc92)  
**Alcance:** revisión estática del código, inspección programática de dos CSV, cotejo de hashes de Git, reproducción aislada del generador de datos y verificación aritmética de métricas y logs. **No** se han reentrenado los cuatro modelos, modificado el repositorio ni ejecutado validación externa.

## 1. Conclusión ejecutiva

El proyecto dispone de materiales reales y trazables para levantar la observación 3: un dataset sintético reproducible para `run_002`, un dataset histórico alternativo para `run_001`, código generador, scripts de ingesta/preprocesamiento/entrenamiento, logs y resultados por cinco folds de cuatro modelos. Sin embargo, **la evidencia no está aún lista para presentarse como experimento definitivo**: existe fuga de información de validación dentro de los folds por escalado previo; faltan matrices exactas del test y AP del test; la base PostgreSQL intermedia no está identificada mediante hash; las dependencias no están fijadas; y aún no existe validación externa con datos de una EPS.

**Hallazgo decisivo de `run_001`:** la regla `label = 1 si clave_lectura_tipo != 0, de lo contrario 0` clasifica correctamente **96,000 de 96,000** registros del backup. Los resultados perfectos de esa corrida **no constituyen evidencia de generalización**. La columna `clave_lectura_tipo` era usada por los modelos y revelaba por completo la etiqueta.

**Hallazgo positivo de `run_002`:** `src/utils/generate_dataset.py` reproduce **exactamente** el CSV actual tras normalizar finales de línea CRLF/LF. La comparación por Git blob confirma que el dataset, generador y resultados aportados corresponden a los archivos publicados en `training`.

## 2. Inventario, procedencia y versionamiento

| Artefacto | Ubicación del repositorio | Verificación |
|---|---|---|
| Dataset de `run_001` | `run_001/dataset_entrenamiento_eps_96000.csv` y `data/dataset_entrenamiento_eps_96000.backup.v1.csv` | mismo Git blob `524080ef5d81e97e1b215cf70ce38aaae994ed49` |
| Resultados de `run_001` | `run_001/resultados_folds.csv` | conservados en la rama; F1=1.0 en los 20 folds |
| Dataset de `run_002` | `run_002/dataset_entrenamiento_eps_96000.csv` y `data/dataset_entrenamiento_eps_96000.csv` | mismo Git blob `4669b99bb14de6e1aa0e69a1aad245deca12f776` |
| Generador de `run_002` | `src/utils/generate_dataset.py` | Git blob `7e7c3866cf85e638eb023e9c847f9321c707569d` |
| Resultados de `run_002` | `run_002/resultados_folds.csv`, `logs/resultados_folds.csv` | mismo Git blob `f24a7a0765149e2310445200177d056094b79915` |
| Entrenamiento | `src/3_model_training.py` | Git blob `191410bd385c4cfec5ce08b5ac209a2b5065efc2` |
| Preprocesamiento | `src/2_model_preprocessing.py` | Git blob `62cce0cd3c81145982dba7c45727417692639ecf` |
| Ingesta | `src/1_data_ingestion.py` | Git blob `3fc06cd6a22fb0044586c97ed1c50284b8e45dab` |
| Logging | `src/utils/logger_setup.py` | Git blob `c4d3108da11c5eef65b2e2cdb31d807637d3fdfb` |
| Configuración | `src/config.py` | Git blob `819cf528217c83bae49b970769546336772c8a02` |

**Nota de integridad:** algunos adjuntos del usuario tienen finales de línea Windows (`CRLF`), mientras que Git guarda las versiones `LF`. Los blobs coinciden después de normalizar únicamente los finales de línea; esto no es una discrepancia de contenido.

**SHA-256 del dataset actual adjunto, tal como se recibió:** `5b3bf2a72a76479e7ff829130080445f62d6f174a4a0621edaf90bdbc6ee4803`  
**SHA-256 del mismo dataset normalizado a LF:** `a26191fbca07a518ed73715d714ed8c6619c4caa1a65637658945e5a0784f25c`  
**SHA-256 del backup `run_001`:** `d96d033178969d9f3f3c2b161aed74ba5201ddbb60cf9f29befb30f87b1c13c3`

La rama `training` estaba **un commit por delante y cero por detrás** de `main` en el momento de consulta. Los logs de entrenamiento y preprocesamiento que se adjuntaron sí fueron inspeccionados localmente, pero las rutas `logs/log_model_training_20261103.log` y `logs/log_model_preprocessing_20261103.log` no estaban publicadas en GitHub (`.gitignore` incluye `*.log`). Para la entrega al jurado, será necesario archivarlos como anexos o evidencias inmutables sin incluir secretos.

## 3. Auditoría de datasets

| Control | `run_001` / backup | `run_002` / actual |
|---|---:|---:|
| Filas | 96,000 | 96,000 |
| Columnas | 27 | 27 |
| `label=0` | 93,212 | 93,148 |
| `label=1` | 2,788 (2.90%) | 2,852 (2.97%) |
| Clientes únicos | 2,000 | 96,000 |
| Lecturas por cliente | 48 | 1 |
| Fechas | 2022–2025 | 2025 |
| Valores faltantes | 0 | 0 |
| Filas idénticas duplicadas | 0 | 0 |

**Hallazgo A — Fuga total en `run_001` (crítico):** En los 96,000 registros se verifica exactamente `label = (clave_lectura_tipo != 0)`. La variable sigue incluida entre las 22 características del pipeline; por eso la ejecución perfecta no es interpretable como capacidad predictiva real. También presenta correlaciones extremadamente altas de `label` con `consumo_m3` y `var_pct_mes`. Sin el código generador histórico, no es posible identificar la intención exacta con que se construyó la etiqueta, pero la relación determinista en el CSV sí está comprobada. En este dataset los 2,000 clientes se repiten 48 veces, por lo que una partición aleatoria por filas comparte clientes entre conjuntos y no sirve para estimar generalización a clientes nuevos.

**Hallazgo B — Reproducibilidad de `run_002` (positivo):** ejecutar el generador adjunto en una ruta temporal aislada produjo un CSV idéntico byte a byte al archivo actual tras convertir `CRLF` a `LF` (96,000 × 27; etiquetas 93,148/2,852). El generador fija `np.random.seed(42)`. Esta prueba no implica que el modelo entrenado se haya reproducido; solo verifica el **dataset**.

**Hallazgo C — Limitación semántica de `run_002` (alto):** cada registro tiene un `cliente_id` distinto. `avg_consumo_6m` y `std_consumo_6m` son valores simulados, **no** calculados de seis lecturas observadas de un mismo cliente; `perfil_cluster_kmeans` se asigna aleatoriamente y **no** procede de un K-Means entrenado; el clima también se genera aleatoriamente. El documento debe describirlos como características sintéticas y no afirmar que hay seguimiento longitudinal, clustering real ni meteorología observada.

**Hallazgo D — Etiquetas sintéticas:** el generador sortea primero `label` y después altera la lectura para `label=1`; por ello el modelo distingue los patrones implantados por la lógica de simulación. Se excluyen adecuadamente `tiene_reclamo` y `reclamo_favor_cliente`, que pueden incorporar información posterior o derivada de la etiqueta. `var_pct_mes` es función de lectura y promedio histórico, disponibles conceptualmente al momento de la evaluación, pero debe verificarse la disponibilidad real futura de estas variables antes de aplicarlo a una EPS. `label=1` no equivale a fraude confirmado mediante inspección.

**Hallazgo E — Inconsistencia de `run_001`:** `var_pct_mes` no coincide necesariamente con la fórmula usada en el generador actual; la diferencia absoluta máxima frente a `round((consumo_m3 - avg_consumo_6m)/avg_consumo_6m, 2)` llega a **6.41**. La fórmula sí se cumple en `run_002` (diferencia máxima: cero).

## 4. Auditoría del pipeline de entrenamiento

Flujo confirmado: CSV → `1_data_ingestion.py` → PostgreSQL (`feature_store_lecturas`) → `2_model_preprocessing.py` → partición estratificada 80/20 (`random_state=42`) → 22 variables y `StandardScaler` → 5-fold `StratifiedKFold` sobre el 80% → XGBoost, Random Forest, SVM-RBF y Soft Voting → `resultados_folds.csv`, escalador y modelo `.pkl`.

### Riesgos metodológicos confirmados

1. **Fuga estadística entre folds:** el escalador se ajusta una vez sobre todo el 80% de entrenamiento **antes** de dividirlo en cinco folds; cada fold de validación aporta estadísticas al escalado de su propio entrenamiento. Corregir integrando el transformador en `Pipeline` dentro de la validación cruzada. **Aclaración:** el escalador no se ajusta con el 20% de test, por lo que **no** se ha demostrado contaminación de ese test por este motivo.
2. **Proporción de clases para XGBoost:** `scale_pos_weight` se calcula sobre todo el 80% y se reutiliza en cada fold. Conviene obtenerla del subconjunto de entrenamiento específico del fold, sin usar el fold de validación.
3. **Orden y trazabilidad del origen:** el preprocesamiento lee PostgreSQL con `ORDER BY timestamp_medicion`, sin segundo criterio para empates; la ingesta reemplaza la tabla con `if_exists='replace'` y no registra hash ni versión del CSV realmente cargado. Aunque los conteos respaldan una fuerte correspondencia con `run_001` y `run_002`, los logs **no prueban el hash exacto** del estado de PostgreSQL empleado.
4. **Selección del ganador:** el programa asigna `best_model` a Soft Voting por nombre, antes de comparar métricas; debe definirse un criterio de selección explícito basado en folds y necesidades de negocio.
5. **Tratamiento de test:** el script calcula `classification_report`, pero no exporta matrices exactas del test, probabilidades, AP de test ni predicciones trazables. La comparación de los cuatro reportes de test podría inducir a seleccionar el modelo mirando el conjunto reservado; debe fijarse selección en entrenamiento/CV y reservar test para evaluación final.
6. **PR-AUC:** el código utiliza `average_precision_score` (Average Precision, AP); conviene nombrar la medida de forma precisa como **AP / resumen de la curva precisión–recall**, no confundirla con integración trapezoidal de la curva.
7. **Persistencia:** se serializan `standard_scaler.pkl` y `hybrid_fraud_model.pkl` por separado, sin manifiesto explícito de orden de 22 características ni versión del pipeline. La ejecución posterior puede sobrescribir artefactos anteriores.
8. **Logging y fallos:** `setup_logger()` sustituye `sys.stdout` varias veces (entrenamiento y preprocesamiento), anida logs, agrega todas las corridas del día al mismo archivo y silencia advertencias. El `except` de entrenamiento imprime error sin relanzarlo, lo que puede ocultar fallos a la automatización.
9. **Entorno:** `requirements.txt` usa cotas inferiores (`>=`), insuficientes para reproducir versiones concretas de NumPy, scikit-learn, XGBoost y Python. Debe añadirse inventario de versiones fijadas y entorno de ejecución.
10. **Inferencia:** el consumidor en GitHub genera `es_mes_festivo=0` siempre (inconsistente con meses 7/12 del generador) y `clave_lectura_tipo=1` por defecto si falta ese campo (mientras el generador asigna 0 con mayor frecuencia). Aunque arma 22 nombres en orden compatible, se necesitan comprobaciones del esquema y distribución de entrada.
11. **Configuración:** `src/config.py` y README contienen credenciales de ejemplo como valores predeterminados. Se recomienda eliminar credenciales del código y usar variables de entorno/plantillas seguras; si alguna clave publicada está en uso real, sustituirla.

## 5. Auditoría de resultados

### Identificación de corridas mediante soporte de clases

- **`run_001`**, log ~01:00 del 03/11/2026: 2,788 positivos (2,230 entrenamiento + 558 test). Coincide con el backup. Los cuatro modelos alcanzan F1=1.0000 y AP=1.0000 en cinco folds; el dataset permite clasificación perfecta por la sola columna `clave_lectura_tipo`.
- **`run_002`**, log ~01:13 del 03/11/2026: 2,852 positivos (2,282 entrenamiento + 570 test). Coincide con el dataset actual; el CSV entregado contiene sus 20 resultados por fold.
- **Intento fallido**, log ~00:29: `No module named 'psycopg'`. No es una tercera corrida válida. La configuración actual referencia `psycopg2`; el log no identifica exactamente qué versión de configuración provocó aquel error.

### `run_002`: resultados por validación cruzada

| Modelo | F1 promedio | Desv. estándar muestral F1 | AP promedio | Desv. estándar muestral AP |
|---|---:|---:|---:|---:|
| XGBoost | 0.65672 | 0.00444 | **0.83250** | 0.01965 |
| Random Forest | 0.63116 | 0.01446 | 0.79972 | 0.01795 |
| SVM-RBF | 0.61624 | 0.01939 | 0.78032 | 0.02570 |
| Soft Voting | **0.76748** | 0.01055 | 0.82668 | 0.01898 |

Los registros por fold son **aritméticamente consistentes**: hay 20 filas, cinco por modelo; cada matriz suma 15,360 observaciones y reproduce el F1 impreso tras redondeo. Soft Voting lidera en F1; **XGBoost lidera en AP**, por lo que no es correcto atribuir superioridad global al ensamble.

### Evaluación del test según log de `run_002` (Soft Voting)

- Soporte de clase normal: **18,630**.
- Soporte de clase irregular: **570**.
- Precisión irregular: **0.76**; recall irregular: **0.79**; F1 irregular: **0.77**; accuracy global redondeada: **0.99**.
- **Limitación:** el log imprime un reporte redondeado, **no** la matriz exacta del test. No debe atribuirse a test la matriz de algún fold. Los conteos `TN=18,530; FP=100; FN=120; TP=450` mencionados anteriormente **no están respaldados** por este log y además no reproducen precisión 0.76; deben excluirse de la tesis salvo nueva prueba verificable.

La prevalencia de irregularidad es 2.97%, por lo cual se debe priorizar precisión, recall, F1, AP y costos de falsos positivos/negativos sobre accuracy aislada.

## 6. Estado de la validación externa

**No se dispone, entre los archivos analizados, de una evaluación con registros reales anonimizados de una EPS y etiquetas confirmadas por expertos.** El holdout del 20% es prueba interna sobre la misma simulación, no validación externa. Debe prepararse un **protocolo externo** separado que especifique procedencia autorizada, periodo y cobertura, unidad de análisis, criterios de etiqueta, controles de privacidad, congelamiento del modelo/umbral antes de evaluar, métricas y decisiones de aprobación. De no haber datos reales, declarar esta evaluación como pendiente; las pruebas sobre un segundo generador serían **robustez sintética**, no validación externa real.

## 7. Matriz de correcciones antes de declarar finalizada la observación 3

| ID | Prioridad | Corrección necesaria | Paso propuesto |
|---|---|---|---|
| H01 | Crítica | Excluir `run_001` como evidencia principal y documentar regla determinista de etiqueta | 2 y 8 |
| H02 | Alta | Documentar alcance real del dataset `run_002` y semántica de las 22 características | 2 |
| H03 | Alta | Ajustar escalador **dentro** del CV; revisar pesos de clase por fold | 3 |
| H04 | Alta | Fijar regla de selección de modelos y reserva del test | 3 |
| H05 | Alta | Guardar matrices exactas, AP de test, scores y métricas completas | 3–5 |
| H06 | Alta | Guardar manifiesto por corrida (dataset/DB, commit, config, seeds, dependencias) | 3–4 y 7 |
| H07 | Alta | Conservar logs de cada corrida sin mezcla, advertencias y estado de ejecución correcto | 3–4 |
| H08 | Alta | Crear protocolo de robustez sintética y de validación externa real, sin resultados inventados | 6 |
| H09 | Media | Verificar esquema/orden de entrada y coherencia de consumidor/modelo/escalador | 3 y 7 |
| H10 | Media | Fijar versiones exactas y procedimiento completo de reproducción | 7 |
| H11 | Media | Retirar/rotar credenciales predeterminadas si estuvieran operativas | 7 |
| H12 | Media | Documentar el dataset previo y sus limitaciones (`var_pct_mes`, múltiples lecturas por cliente) | 2 y 8 |

## 8. Criterio de cierre del Paso 1

**Auditoría ejecutada.** Han quedado identificadas las desviaciones metodológicas y de reproducibilidad, establecida la causa directa de los resultados perfectos de `run_001` y comprobada la reproducibilidad aislada del generador de `run_002`.

**No realizado en el Paso 1 (deliberadamente):** corrección de scripts, cambios de datasets, escritura de commits en GitHub, nuevo entrenamiento, validación externa y redacción final de anexos. Estas actuaciones pertenecen a los siguientes pasos y requieren autorización del usuario.

**Decisión propuesta para el Paso 2:** utilizar `run_002` como candidato principal de dataset sintético, conservar `run_001` como antecedente histórico no válido para la estimación principal y crear una ficha de datos que exponga honestamente las limitaciones de simulación. Esta es una propuesta, no una decisión ejecutada.
