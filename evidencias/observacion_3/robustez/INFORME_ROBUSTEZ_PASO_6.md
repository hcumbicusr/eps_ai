# SIDI — Paso 6: evaluación de robustez con datos sintéticos independientes

**Experimento:** SIDI-STRESS-001 · **Fecha:** 4 de noviembre de 2026 · **Estado:** ejecutado y documentado.  
**Modelo:** `selected_pipeline.joblib` procedente de SIDI-RUN-003; SHA-256 `663c5d8d925a08b1deb25d04a2d9222af469ec0313072478ee09a3449a1a7969`.  
**Alcance:** **solo pruebas de estrés sintéticas**. No existen datos reales de una EPS; no se realizó validación externa real.  
**Fuente del modelo:** `SIDI_RUN_003_evidencias_completas_paso_4.zip`, `experiments/run_003/selected_pipeline.joblib`. 

## 1. Propósito y diseño

Se evaluó el modelo congelado y previamente seleccionado a partir de SIDI-DATA-002 frente a **60 000 registros sintéticos nuevos**, generados con un código diferente del generador original y cinco semillas independientes. No se emplearon filas de SIDI-DATA-002 ni del test interno de SIDI-RUN-003, no se reentrenó ningún componente ni se optimizó el umbral. La etiqueta en estos datos representa **una irregularidad simulada por reglas**, no una inspección ni un fraude verificado.

El diseño de los cinco escenarios se fijó en `protocolo_predefinido_SIDI_STRESS_001.json` antes de calcular las métricas. Cada escenario tiene 12 000 registros. Se mantuvieron las 22 características en el orden del artefacto, `StandardScaler` dentro del modelo y clasificación positiva con probabilidad **≥ 0.50**. Se midieron F1, precisión, recall, Average Precision (AP), exactitud, ROC-AUC y matriz de confusión.

No se reutilizó el generador original: el nuevo generador usa un perfil de consumo histórico lognormal, estacionalidad sinusoidal, ruido relativo, irregularidades expresadas mediante multiplicadores independientes, y algunas variaciones legítimas extremas de consumo en un escenario especial. Las variables no relacionadas con la etiqueta se simularon sin utilizar la etiqueta. Los escenarios no son estimaciones de prevalencia ni de severidad observadas en una EPS.

## 2. Escenarios definidos

- **S0 — Referencia sintética alternativa:** prevalencia 3%; consumo y desviaciones generados con nuevas distribuciones y multiplicadores moderados.
- **S1 — Irregularidades leves:** prevalencia 3%; desviaciones de consumo pequeñas respecto al consumo base, diseñadas para evaluar sensibilidad a patrones sutiles.
- **S2 — Cambio de perfil:** prevalencia 3%; mayor consumo medio y dispersión, representando desplazamiento de distribución de variables.
- **S3 — Variaciones normales extremas:** prevalencia 3%; 12% de registros negativos presenta consumos legítimamente extremos por construcción. Se prueba sensibilidad a falsos positivos bajo ambigüedad sintética.
- **S4 — Mayor prevalencia:** prevalencia 12%, manteniendo la mecánica moderada; se explora dependencia de las métricas respecto a la tasa de casos positivos.

## 3. Resultados

| Escenario | N | Positivos | F1 | AP | Precisión | Recall | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Referencia alternativa | 12,000 | 360 | 0.7338 | 0.7699 | 0.7013 | 0.7694 | 118 | 83 |
| Irregularidades leves | 12,000 | 360 | 0.0828 | 0.0753 | 0.1626 | 0.0556 | 103 | 340 |
| Cambio de perfil | 12,000 | 360 | 0.4773 | 0.5080 | 0.4184 | 0.5556 | 278 | 160 |
| Variaciones normales extremas | 12,000 | 360 | 0.2918 | 0.1558 | 0.1805 | 0.7611 | 1,244 | 86 |
| Prevalencia 12% | 12,000 | 1,440 | 0.7968 | 0.8847 | 0.8875 | 0.7229 | 132 | 399 |

**Control de referencia:** el test interno SIDI-RUN-003 mostró F1=0.7617, AP=0.8216, precisión=0.7692 y recall=0.7544 sobre 19 200 registros de su propio generador. **No** debe confundirse ese conjunto con los nuevos escenarios: fueron construidos mediante mecanismos distintos. La comparación con S0 es descriptiva, no una prueba estadística de superioridad ni un estimador de rendimiento real.

## 4. Interpretación para la investigación

1. **Generalización sintética parcial:** S0 obtuvo F1=0.7338 y recall=0.7694, cercanos, aunque inferiores, al test interno de SIDI-RUN-003. Esto respalda una capacidad de detección en un segundo mecanismo simulado de anomalías moderadas, no en EPS reales.
2. **Fragilidad ante anomalías leves:** S1 alcanzó F1=0.0828 y recall=0.0556; de 360 anomalías simuladas, 340 fueron omitidas. El clasificador no debe presentarse como detector robusto de desviaciones sutiles.
3. **Sensibilidad a desplazamiento de distribución:** S2 registró F1=0.4773, con 278 falsos positivos. Cambios de perfil de consumo pueden alterar el balance precisión–recall.
4. **Falsas alertas ante cambios legítimos:** en S3 hubo 1,244 falsos positivos entre 11,640 normales (10.69% de tasa de falsos positivos), frente a 118 en S0. Aquí "legítimo" es una etiqueta sintética impuesta, no validación operacional.
5. **Efecto de prevalencia:** S4 elevó la proporción positiva de 3% a 12% y obtuvo F1=0.7968. La mejora de precisión/AP puede deberse en parte al cambio de prevalencia; no demuestra mayor habilidad del modelo ni mayor generalización.

Las diferencias entre escenarios reflejan tanto la reacción del modelo como **supuestos arbitrados por el diseñador de los escenarios**. Los ejemplos nuevos no fueron muestreados de una población real conocida; por ello no se deben inferir métricas poblacionales, tasas de fraude, costos o resultados comerciales de una EPS.

## 5. Controles de reproducibilidad e integridad

- La ejecución comprobó el SHA-256 del modelo antes de cargarlo y no realizó `fit`, ajuste de umbral ni cambios del pipeline.
- Se registraron semillas 6111–6115, tamaño, reglas de cada escenario y umbral fijo en la configuración previa.
- Los cinco datasets de 27 columnas se regeneraron desde el código de estrés y coincidieron **byte a byte** con los CSV archivados.
- Se guardaron predicciones por observación, matrices derivables, métricas por escenario y SHA-256 por archivo.
- Los 60 000 identificadores de estos escenarios son sintéticos, nuevos y no coinciden con los identificadores originales que usan formato `C#####`.
- Se verificaron etiquetas, dimensiones, finitud, consistencia de predicción (`score ≥ 0.5`), matrices y recuentos de clases.
- La ejecución inicial presentó un error de formato de fecha, corregido antes de emitir predicción alguna. La primera corrida de evaluación terminó por límite de duración después de cuatro escenarios; el quinto se finalizó desde el dataset ya generado. Ambos eventos quedaron conservados en el registro metodológico.

## 6. Limitaciones y conclusión

Se trata de **robustez sintética entre generadores**, no de validación externa realizada con una EPS, ni de pruebas de campo, ni de estimación prospectiva de impacto. Los datos de entrenamiento y estrés comparten todavía supuestos de diseño del investigador, como usar consumo relativo a un promedio simulado para definir anomalías. La verdadera transferencia a una EPS debe quedar pendiente.

**Conclusión académica delimitada:** El SIDI mostró un desempeño razonable en un escenario sintético alternativo de anomalías moderadas; sin embargo, su F1 disminuyó notablemente ante irregularidades leves, desplazamientos de perfil y cambios normales extremos. En consecuencia, los resultados del SIDI-RUN-003 no justifican afirmar robustez generalizada ni desplegar decisiones automáticas en una EPS real. Las pruebas constituyen un análisis exploratorio de sensibilidad que identifica condiciones bajo las cuales el clasificador requiere validación adicional.

**Evidencia:** archivo `artefactos/scenario_metrics.csv`, cinco `dataset_*.csv`, cinco `predictions_*.csv`, `integrity_checks.json`, `reproducibility_checks.json`, `generate_and_evaluate_sidi_stress_001.py`, configuración congelada y manifiesto SHA-256.
