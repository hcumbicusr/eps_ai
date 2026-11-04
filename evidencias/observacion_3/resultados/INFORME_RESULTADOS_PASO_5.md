# SIDI — Paso 5. Consolidación e interpretación de resultados

**Experimento:** SIDI-RUN-003  
**Datos:** SIDI-DATA-002 (96,000 registros 100% sintéticos)  
**Fuente primaria:** paquete `SIDI_RUN_003_evidencias_completas_paso_4.zip`  
**Referencia de código base documentada:** rama `training`, commit `d2cdc2dc120bbb9aef643ac9e6035f179170fc92`  
**Fecha de preparación:** 4 de noviembre de 2026  
**Alcance:** análisis estadístico descriptivo de resultados ya producidos. No se ejecutó un nuevo entrenamiento ni se modificó GitHub.

## 1. Objetivo y alcance

Consolidar, recalcular e interpretar los resultados del experimento definitivo de clasificación binaria del SIDI, con énfasis en la detección de la clase irregular simulada (`label=1`). Estos resultados permiten documentar el desempeño **dentro del escenario sintético y del generador utilizados**. No representan mediciones operativas reales ni validación externa con datos de una EPS.

## 2. Configuración experimental auditada

- 96,000 registros; 93,148 normales y 2,852 irregulares sintéticos (2.9708%).
- 27 columnas iniciales; 22 características predictoras y una etiqueta objetivo.
- Hold-out estratificado: 76,800 registros de entrenamiento/CV (2,282 irregulares) y 19,200 registros reservados para prueba (570 irregulares).
- Validación cruzada: cinco folds estratificados sobre el 80% de entrenamiento; cada validación contiene 15,360 registros.
- `StandardScaler` ajustado exclusivamente dentro del `Pipeline` en los datos de ajuste de cada fold.
- Cuatro candidatos: XGBoost, Random Forest, SVM RBF y ensamble Soft Voting.
- Selección previa al test: máximo F1 medio por fold; AP medio como primer desempate.
- Test reservado evaluado una vez tras la selección, con umbral fijo de clasificación de 0.50.
- AP significa `average_precision_score`, **no** área trapezoidal bajo la curva PR.

## 3. Comparación de modelos en validación cruzada

| Modelo | F1 medio | DE F1 | AP media | Precisión media | Recall medio |
|---|---:|---:|---:|---:|---:|
| Soft Voting | 0.7817 | 0.0152 | 0.8262 | 0.7993 | 0.7656 |
| SVM RBF | 0.7487 | 0.0091 | 0.7817 | 0.8804 | 0.6516 |
| Random Forest | 0.6998 | 0.0191 | 0.8022 | 0.6306 | 0.7870 |
| XGBoost | 0.6643 | 0.0148 | 0.8329 | 0.5582 | 0.8212 |

**Hallazgo:** Soft Voting obtiene el mayor F1 medio (0.7817); XGBoost registra la mayor AP media (0.8329). Los resultados no demuestran superioridad universal ni diferencias estadísticamente significativas. La desviación estándar entre cinco folds describe variación interna, no incertidumbre externa.

![Figura 1. Comparación F1](figura_01_f1_comparacion_cv.png)

![Figura 2. AP](figura_02_average_precision_cv.png)

### 3.1. Cinco folds de Soft Voting

| Fold | F1 | AP | Precisión | Recall | VP | FP | FN |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.7822 | 0.8207 | 0.7928 | 0.7719 | 352 | 92 | 104 |
| 2 | 0.7717 | 0.8305 | 0.7651 | 0.7785 | 355 | 109 | 101 |
| 3 | 0.7954 | 0.8379 | 0.8411 | 0.7544 | 344 | 65 | 112 |
| 4 | 0.7973 | 0.8482 | 0.8072 | 0.7877 | 360 | 86 | 97 |
| 5 | 0.7619 | 0.7935 | 0.7906 | 0.7352 | 336 | 89 | 121 |

El F1 fluctúa entre 0.7619 y 0.7973, con desviación estándar muestral 0.0152. Los 20 resultados de todos los modelos se entregan en `tabla_02_resultados_20_folds.csv`.

![Figura 3. F1 por fold](figura_03_f1_por_fold.png)

## 4. Evaluación del test sintético reservado

El modelo elegido por CV fue entrenado con las 76,800 observaciones del conjunto de entrenamiento y evaluado posteriormente sobre 19,200 observaciones no utilizadas para la selección.

| Métrica | Valor |
|---|---:|
| F1 clase irregular | 0.7617 |
| Precisión clase irregular | 0.7692 (76.92%) |
| Recall clase irregular | 0.7544 (75.44%) |
| Average Precision (AP) | 0.8216 |
| ROC-AUC | 0.9631 |
| Exactitud global (accuracy) | 0.9860 (98.60%) |
| Especificidad | 0.9931 (99.31%) |
| Tasa de falsas alertas entre normales (FPR) | 0.69% |
| Tasa de irregularidades omitidas (FNR) | 24.56% |

**Matriz de confusión (filas: clase real; columnas: predicción):**

| Real / Predicho | Normal | Irregular | Total |
|---|---:|---:|---:|
| Normal | 18,501 (VN) | 129 (FP) | 18,630 |
| Irregular | 140 (FN) | 430 (VP) | 570 |
| **Total** | **18,641** | **559** | **19,200** |

![Figura 4. Matriz de confusión](figura_04_matriz_confusion_test.png)

### 4.1. Lectura técnica de errores y alertas

Se identificaron 430 de 570 casos irregulares simulados (75.44%); se omitieron 140 (24.56%). De 18,630 observaciones normales simuladas, 129 recibieron una alerta falsa (0.69% de normales). De 559 alertas emitidas, 430 correspondieron a irregularidades simuladas (76.92%) y 129 fueron falsos positivos (23.08% de alertas). La exactitud global (98.60%) es alta en parte porque predominan los consumos normales; por ello se priorizan F1, precisión, recall y AP para evaluar la clase minoritaria.

**No interpretar** estas cantidades como inspecciones reales, fraude confirmado, ahorro económico, afectación de facturación o desempeño asegurado en EPS. Esos efectos no se midieron.

### 4.2. Coherencia entre CV y test

F1 medio de CV = 0.7817, frente a F1 de test = 0.7617, diferencia descriptiva = 0.0200 puntos absolutos. Ambos provienen del mismo generador sintético, por lo que su proximidad no demuestra generalización entre distribuciones ni ausencia de sesgos de simulación.

## 5. Contraste histórico con RUN-002 (solo descriptivo)

| Modelo | RUN-002 F1 medio | RUN-003 F1 medio | Diferencia |
|---|---:|---:|---:|
| Soft Voting | 0.7675 | 0.7817 | +0.0142 |
| SVM RBF | 0.6162 | 0.7487 | +0.1325 |
| Random Forest | 0.6312 | 0.6998 | +0.0687 |
| XGBoost | 0.6567 | 0.6643 | +0.0076 |

RUN-002 empleó otro procedimiento de preprocesamiento y evaluación. Las diferencias incluyen cambios metodológicos y de ejecución, no un experimento controlado de ablación. En consecuencia, **no se atribuye causalmente** la diferencia de F1 a un componente concreto. RUN-001, cuyo dataset tenía una característica determinista de la etiqueta, no se emplea como línea de base válida.

## 6. Limitaciones de interpretación

1. **Simulación:** la etiqueta `label` y los patrones de consumo son producidos algorítmicamente; no existe etiquetado externo de inspecciones.
2. **Sin datos reales:** no se dispone de mediciones de una EPS; no se ha ejecutado validación externa real.
3. **Misma familia de generación:** tanto CV como test del RUN-003 proceden del mismo dataset/generador. El test es un hold-out independiente en filas, no una muestra externa de otro origen.
4. **Unidad de análisis:** el dataset actual usa un identificador de cliente único por fila. No demuestra predicción longitudinal sobre sucesivas lecturas reales de un mismo usuario.
5. **Selección de métricas:** F1 depende del umbral 0.50; la AP evalúa el ordenamiento de puntuaciones. No se realizó optimización de umbral para despliegue real.
6. **Comparación histórica:** RUN-002 y RUN-003 no son corridas metodológicamente idénticas. No se presentan pruebas de significancia o intervalos de confianza basados en los folds.
7. **Estado de integración:** el nuevo pipeline completo no fue desplegado en los consumidores existentes de FastAPI/RabbitMQ.

## 7. Redacción propuesta para la tesis

> Para evaluar la capacidad de clasificación del componente de inteligencia artificial del Sistema Inteligente de Detección de Irregularidades (SIDI), se utilizó un conjunto de 96,000 registros completamente sintéticos, de los cuales 2,852 fueron etiquetados como irregulares simulados. Se realizó una partición estratificada de 80% para entrenamiento y validación cruzada y 20% para prueba final, manteniendo la transformación de escalado dentro de cada fold de entrenamiento. Se compararon cuatro alternativas: XGBoost, Random Forest, SVM con kernel RBF y un ensamble híbrido de votación blanda (Soft Voting). El ensamble obtuvo el mayor F1 promedio en cinco folds (0.7817; desviación estándar 0.0152) y fue seleccionado conforme al criterio preestablecido. En el conjunto de prueba reservado alcanzó precisión de 0.7692, sensibilidad de 0.7544, F1 de 0.7617 y Average Precision de 0.8216. La matriz de confusión registró 430 verdaderos positivos, 18,501 verdaderos negativos, 129 falsos positivos y 140 falsos negativos. Estos resultados muestran capacidad de identificación de patrones irregulares dentro del escenario de simulación definido, sin constituir validación externa ni prueba de desempeño sobre registros reales de empresas prestadoras de servicios de saneamiento.

## 8. Evidencias y referencias internas

- `experiments/run_003/cv_folds.csv`: 20 métricas originales por fold.
- `experiments/run_003/cv_resumen.csv` y `experiments/run_003/model_selection.json`: consolidación y selección anterior al test.
- `experiments/run_003/test_predictions.csv`, `test_metrics.json` y `test_confusion_matrix.csv`: evaluación final verificable.
- `experiments/run_003/partition_summary.json`, `splits.npz` y `protocol_config.json`: particiones y protocolo.
- `verificacion_evidencias_RUN_003.json`: 18 controles aprobados en el paso 4.
- `tabla_01_comparacion_modelos_cv.csv`, `tabla_02_resultados_20_folds.csv`, `tabla_03_matriz_test.csv`, `tabla_04_comparacion_historica_run002_run003.csv`: tablas elaboradas en este paso a partir de la evidencia anterior.

**Estado del paso 5:** cerrada la consolidación estadística y redacción interpretativa. El paso 6 (robustez sintética / protocolo externo futuro) queda pendiente de GO explícito.
