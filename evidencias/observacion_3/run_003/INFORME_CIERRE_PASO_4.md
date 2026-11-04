# SIDI — Cierre del Paso 4: ejecución experimental SIDI-RUN-003

**Estado:** COMPLETADA Y VERIFICADA, sobre **dataset 100% sintético**. **No** se hizo validación externa con una EPS real.

## 1. Identidad y aislamiento

- Protocolo: `SIDI-RUN-003`; datos: `SIDI-DATA-002`; commit Git documentado: `d2cdc2dc120bbb9aef643ac9e6035f179170fc92`.
- Dataset: 96,000 registros, 27 columnas; 22 entradas predictoras; 2,852 etiquetas positivas simuladas.
- SHA-256 de contenido CSV normalizado LF: `a26191fbca07a518ed73715d714ed8c6619c4caa1a65637658945e5a0784f25c`.
- Estratificación 80/20: entrenamiento/CV 76,800 (2,282 positivos); test reservado 19,200 (570 positivos); cinco folds de validación interna.
- Código experimental aislado del despliegue: **no se modificó el repositorio GitHub, no se escribió PostgreSQL y no se reemplazaron `models/hybrid_fraud_model.pkl` ni `models/standard_scaler.pkl`**.
- Entorno efectivo: Python 3.13.5; scikit-learn 1.8.0; XGBoost 3.1.3; NumPy 2.3.5; pandas 2.2.3; joblib 1.5.3.

## 2. Orquestación y equivalencia

La primera ejecución **secuencial** quedó deliberadamente **incompleta** y se conservó `run.log` por alto costo de SVM probabilístico. Para la ejecución definitiva se utilizó `src/experiments/sidi_run_003_parallel.py` (incluido en el paquete), con estos ajustes exclusivamente computacionales:

1. Los tres modelos base se entrenaron en cada uno de los mismos cinco folds, usando los mismos hiperparámetros y semillas que el protocolo definido en el Paso 3.
2. Los folds independientes se ejecutaron en cuatro procesos (`loky`, `n_jobs=4`), sin alterar las particiones ni las etiquetas.
3. Las probabilidades de los tres modelos base en cada fold se promediaron con pesos iguales, operación matemáticamente equivalente al `VotingClassifier(voting='soft')` que usa el mismo escalador y los mismos estimadores. Se verificó por prueba automatizada sobre datos artificiales ajenos al dataset SIDI.
4. El modelo final ganador **sí fue entrenado como `Pipeline(StandardScaler(), VotingClassifier(...))`**, no como un promedio guardado manualmente.

Los archivos de ejecución y el código de la orquestación exacta están conservados para permitir su revisión. La variante paralela todavía **no está subida a GitHub**.

## 3. Resultados de validación cruzada (5 folds)

| Modelo | F1 medio | F1 desviación estándar muestral | AP medio |
|---|---:|---:|---:|
| Modelo Hibrido (Soft Voting) | 0.7817 | 0.0152 | 0.8262 |
| SVM (Kernel RBF) | 0.7487 | 0.0091 | 0.7817 |
| Random Forest | 0.6998 | 0.0191 | 0.8022 |
| XGBoost | 0.6643 | 0.0148 | 0.8329 |

**Ganador predefinido por F1 medio:** `Modelo Hibrido (Soft Voting)`. AP solo para desempate; no se consultó test durante selección. AP corresponde a `average_precision_score`, no a una aproximación trapezoidal PR-AUC.

## 4. Evaluación final del conjunto test (una sola vez)

| Métrica o cantidad | Resultado |
|---|---:|
| F1 clase irregular | 0.7617 |
| Average Precision (AP) | 0.8216 |
| Precisión clase irregular | 0.7692 |
| Recall clase irregular | 0.7544 |
| Accuracy global | 0.9860 |
| ROC-AUC | 0.9631 |
| Verdaderos negativos (VN) | 18501 |
| Falsos positivos (FP) | 129 |
| Falsos negativos (FN) | 140 |
| Verdaderos positivos (VP) | 430 |

Matriz de confusión exacta, fila real / columna predicha:

| Clase real | Predicho normal | Predicho irregular |
|---|---:|---:|
| Normal | 18501 | 129 |
| Irregular | 140 | 430 |

Estas cifras derivan de `test_predictions.csv`, `test_metrics.json` y `test_confusion_matrix.csv`. El archivo `test_predictions.csv` permite auditoría matemática sin volver a entrenar ni optimizar parámetros con el test.

## 5. Aceptación y evidencias

- Controles técnicos posteriores a la ejecución: **18/18 aprobados** (`verificacion_evidencias_RUN_003.json`).
- Pruebas automatizadas pre-ejecución: **8/8 aprobadas** (7 originales + equivalencia de soft voting).
- Smoke test de inferencia: **aprobado**, usando exclusivamente 5 filas del 80% de entrenamiento; sin segunda evaluación del test.
- Modelo completo `selected_pipeline.joblib`: `Modelo Hibrido (Soft Voting)`; SHA-256 `663c5d8d925a08b1deb25d04a2d9222af469ec0313072478ee09a3449a1a7969`; incluye escalado interno, no desplegado.
- Artefactos originales en la carpeta `experiments/run_003/` (20 folds, configuración, scripts, índices splits, modelo, inferencias, logs, dependencias y hashes).

## 6. Limitaciones y pendientes (sin avanzar al Paso 5)

- Es una **validación interna de datos generados algorítmicamente**: la prueba 20% no prueba generalización a EPS reales.
- No hay validación externa realizada con datos reales ni dictamen experto de casos.
- El código de inferencia actual de FastAPI/RabbitMQ aplica el escalador por fuera, de modo que **NO puede sustituirse su modelo actual por este pipeline sin actualizar y probar los consumidores**.
- El entorno de esta ejecución usa Python 3.13.5, no Python 3.11 del README del repositorio. Sus dependencias exactas quedan en `requirements_freeze.txt`.
- La comparación interpretativa con `run_001`/`run_002`, la discusión de las métricas y elaboración de figuras corresponden al **Paso 5**, que no se inicia sin GO.

## 7. Procedimiento de reproducción

Ver `LEEME_REPRODUCIBILIDAD_PASO_4.md`. El dataset original permanece en GitHub, rama `training`, ruta `data/dataset_entrenamiento_eps_96000.csv`.
