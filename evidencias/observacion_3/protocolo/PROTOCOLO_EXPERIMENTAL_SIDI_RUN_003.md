# SIDI — Protocolo experimental predefinido SIDI-RUN-003

**Versión documental:** 1.0 (propuesta sometida a revisión del investigador).  
**Fecha de elaboración:** 4 de noviembre de 2026.  
**Objetivo:** subsanar el componente de entrenamiento de la observación 3 mediante evidencia reproducible y sin contaminación metodológica.  
**Estado:** **DISEÑADO Y VERIFICADO EN PRE-FLIGHT; NO EJECUTADO EN EL PASO 3.**  
**Alcance:** evaluación *interna* de modelos sobre **datos totalmente sintéticos**. No existe validación externa con datos reales de una EPS.

## A. Datos y unidad de análisis

- Dataset: **SIDI-DATA-002**, 96,000 filas y 27 columnas, 2,852 etiquetas positivas simuladas (2.9708%).
- Ruta canónica: `data/dataset_entrenamiento_eps_96000.csv`; copia histórica idéntica en `run_002/`.
- Trazabilidad: `protocolos/SIDI_DATA_002_manifest.json` contiene **SHA-256 normalizado a LF**, commit de auditoría y el **orden de las 22 entradas predictoras**.
- Generación: `src/utils/generate_dataset.py` produce la etiqueta por simulación y modifica el consumo en función de la clase. No representa fraude confirmado por inspección.
- Unidad: **una lectura por identificador sintético único**; no hay series longitudinales empíricas por cliente. `avg_consumo_6m`, `std_consumo_6m`, `ceros_ult12` y `perfil_cluster_kmeans` son valores sintéticos, no cálculos históricos/K-Means reales.
- Exclusiones: `cliente_id`, `timestamp_medicion`, `tiene_reclamo`, `reclamo_favor_cliente` y `label`. Las columnas de reclamos se excluyen para evitar señales construidas a partir de la etiqueta o posteriores al evento.
- Rechazar el entrenamiento si el hash, nombre/orden de columnas, cantidades, clases o finitud de características no coincide con el manifiesto. Cualquier corrección de datos exige nuevo ID/versionado y nueva justificación.

## B. División y evaluación interna

1. Leer **directamente el CSV oficial verificado**. No leer la tabla `feature_store_lecturas` para este experimento porque una tabla cargada previamente no tiene prueba criptográfica de correspondencia con el CSV. La arquitectura con PostgreSQL puede conservarse para otros componentes del sistema, pero la fuente científica del experimento es el archivo versionado.
2. Fijar `random_seed=42` y realizar división **80% entrenamiento (76,800) / 20% prueba final (19,200)** con `train_test_split(..., stratify=y, random_state=42)`.
3. Conservar los identificadores de filas de ambos conjuntos en `splits.npz`. El **test queda aislado** y no participa en la elección de modelos, transformaciones, selección de hiperparámetros ni ajuste de umbral.
4. En las 76,800 observaciones de entrenamiento, ejecutar **StratifiedKFold(n_splits=5, shuffle=True, random_state=42)**: cada validación tiene 15,360 registros. Registrar índices y balance de clases de cada fold.
5. En cada fold, **construir un Pipeline nuevo** `StandardScaler -> clasificador` y hacer `fit` exclusivamente sobre los índices del fold de ajuste. Transformar el fold de validación por medio de ese mismo Pipeline. Ninguna estadística del fold de validación participa en el ajuste del escalador.
6. Calcular `scale_pos_weight = n_neg/n_pos` para XGBoost **con las etiquetas del subconjunto del fold de ajuste**. `class_weight="balanced"` de RF/SVM se calcula dentro del entrenamiento correspondiente. La calibración interna de `SVC(probability=True)` se realiza exclusivamente con los datos de ajuste del fold.
7. Repetir para los cuatro modelos: XGBoost, Random Forest, SVM RBF y Soft Voting (XGBoost + RF + SVM). Usar los hiperparámetros **predefinidos** en `protocolos/SIDI_RUN_003_config.json`. No realizar búsqueda ni ajuste de hiperparámetros en esta corrida.
8. Registrar por fold F1, **Average Precision (AP)**, precisión, recall, accuracy, ROC-AUC, VP, VN, FP y FN. En todos los modelos la predicción binaria se define como **`predict_proba(clase 1) >= 0.50`**; esto unifica el criterio de clasificación, incluso en SVM, donde `predict()` puede diferir de un umbral 0.50 sobre `predict_proba()`.

### Nota sobre PR-AUC

Los archivos históricos llamaron `PR-AUC` al resultado de `sklearn.metrics.average_precision_score`. En esta corrida se usará **AP**, el nombre técnico exacto de esa métrica, para evitar confundirla con el cálculo trapezoidal del área bajo la curva Precision-Recall. La columna `AP` del nuevo CSV se corresponde con la función utilizada históricamente.

## C. Selección y prueba final

- **Criterio principal predefinido:** mayor **F1 promedio** en los cinco folds. El F1 es apropiado para el desbalance simulado (aproximadamente 3% de positivos) y equilibra precisión y recuperación de casos irregulares.
- **Desempate:** mayor **AP promedio**; si persistiera igualdad exacta, se conserva el orden de modelos declarado en la configuración. Se compara sin redondear.
- Reportar desviación estándar muestral de cinco folds (ddof=1), sin presentar los folds como cinco pruebas externas independientes.
- **No** seleccionar automáticamente Soft Voting por su nombre. Si gana otro modelo según la regla anterior, informarlo y discutir la diferencia con el objetivo del modelo híbrido; no modificar el criterio tras conocer el resultado.
- Ajustar **únicamente al modelo seleccionado** con todo el 80% de entrenamiento, usando un Pipeline nuevo. Calcular y guardar las métricas y matriz de confusión del **20% test una sola vez**, después de seleccionar por CV.
- No cambiar umbral 0.50 ni hiperparámetros a partir del test. Una nueva propuesta metodológica requeriría experimento versionado y nuevo test independiente.

## D. Artefactos obligatorios previstos para el Paso 4

La ejecución aprobada deberá crear una carpeta única `experiments/run_003/`, **sin sobrescribir** la carpeta de un experimento anterior, con:

| Archivo | Contenido |
|---|---|
| `run.log` | Inicio, modelos, folds, métricas, selección y errores |
| `protocol_config.json` | Parámetros inmutables utilizados |
| `dataset_manifest.json` | Hash y esquema del dataset |
| `environment.json` y `requirements_freeze.txt` | Entorno de ejecución y versiones reales instaladas |
| `splits.npz` | Índices originales de entrenamiento, test y cinco folds |
| `partition_summary.json` | Cantidad y balance de clases por partición |
| `cv_folds.csv` | 20 filas completas (4 modelos × 5 folds) |
| `cv_resumen.csv` | Medias y desviaciones estándar por modelo |
| `model_selection.json` | Selección con criterio predefinido y clasificación de modelos |
| `test_metrics.json` | Métricas del test del ganador |
| `test_confusion_matrix.csv` | Matriz exacta del test, orden normal/irregular |
| `test_classification_report.json` | Informe completo por clase |
| `test_predictions.csv` | Índice original, etiqueta simulada, score, predicción |
| `selected_pipeline.joblib` y `artifact_manifest.json` | Escalador + modelo juntos, nombre, hash, lista ordenada de características |

**El archivo `selected_pipeline.joblib` NO es compatible automáticamente con consumidores que aplican un `StandardScaler` externo antes de `model.predict_proba()`.** Un consumidor deberá adaptarse y validarse antes de desplegarlo. No reemplazar `models/hybrid_fraud_model.pkl` ni `models/standard_scaler.pkl` en el Paso 4.

## E. Alcance y límites

- Estos resultados estimarán comportamiento **interno dentro de una simulación**. Incluso un test reservado del mismo generador sintético **no es validación externa**.
- La validación con datos sintéticos de **escenarios independientes y modificados**, propuesta para el Paso 6, se reportará como *robustez sintética*, nunca como validación externa sobre EPS real.
- No hay datos reales de ninguna EPS; por tanto, se presentará un **protocolo futuro de validación externa**, indicando expresamente que no se ejecutó y evitando afirmar sensibilidad, precisión o impacto real en operación.
- Las puntuaciones del modelo no están calibradas como probabilidades reales de fraude y el umbral 0.50 es una regla experimental fija, no un umbral optimizado por costos operativos.
- El rendimiento de `run_001` (F1=1.0) no integra la comparación principal, dado que su característica `clave_lectura_tipo` revela la etiqueta. Los resultados previos de `run_002` se conservan como antecedentes, sin mezclarlos en la tabla de `run_003`.

## F. Criterio de aceptación de la ejecución futura

1. El hash del CSV oficial y el orden de sus 22 características coinciden con el manifiesto.
2. No hay intersecciones entre test y entrenamiento/CV, ni entre los subconjuntos de ajuste y validación de cada fold.
3. El escalador se aprende **dentro de cada fold**; parámetros del modelo computados solo con su subconjunto de ajuste.
4. Los 20 registros CV están presentes y sus métricas/matrices son aritméticamente consistentes.
5. La selección es por F1 medio de CV, sin consultar el test; AP solo desempata.
6. Existe **una evaluación final** del modelo ganador sobre el test, con matriz exacta y reporte.
7. Entorno, parámetros, particiones, evidencias y modelo quedan serializados en carpeta exclusiva.
8. Ningún resultado se presenta como validación externa real.

**Esta es una propuesta de protocolo; su ejecución requiere GO del investigador para el Paso 4.**
