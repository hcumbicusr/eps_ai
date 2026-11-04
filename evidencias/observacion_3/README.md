# Evidencias de investigación — Observación 3 (SIDI)

**Alcance:** investigación aplicada sobre **datos 100 % sintéticos**. No existe acceso a datos históricos reales de una EPS. Ningún documento de esta carpeta implica validación externa ejecutada con datos reales.

## Lectura recomendada

1. `datos/` y `../../protocolos/SIDI_DATA_002_manifest.json`: dataset oficial SIDI-DATA-002, 96 000 registros, 27 columnas; 22 predictoras, 5 excluidas. El CSV original ya está en `data/dataset_entrenamiento_eps_96000.csv`.
2. `auditoria/`: revisión de las ejecuciones antiguas y por qué RUN-001 es inadecuada como evaluación principal (variable que identifica la etiqueta).
3. `protocolo/`: metodología definida antes de SIDI-RUN-003; partición 80/20 estratificada, semilla 42, cinco folds dentro del 80 %, selección por F1 medio (desempate AP).
4. `run_003/`: evaluación corregida; 20 folds, tablas, matriz, test único y datos de reproducibilidad.
5. `resultados/`: consolidación de tablas y discusión del desempeño.
6. `robustez/`: cinco escenarios sintéticos nuevos; **no equivalen a validación externa real**.

## Resultados principales verificados

- SIDI-RUN-003: Soft Voting gana por F1 medio de CV = **0.7817**, AP media **0.8262** (XGBoost obtiene la mayor AP entre modelos).
- Test sintético reservado: F1 **0.7617**, AP **0.8216**, precisión **0.7692**, sensibilidad **0.7544**; TN=18 501, FP=129, FN=140, TP=430.
- SIDI-STRESS-001: F1 entre **0.0828 y 0.7968** según escenario; el alto valor con mayor prevalencia no indica mejora del modelo.

## Reproducibilidad desde la raíz del repositorio

1. Usar un entorno virtual compatible con el Python indicado en `run_003/environment.json` (ejecución original: Python 3.13.5, scikit-learn 1.8.0, XGBoost 3.1.3). `run_003/requirements_freeze.txt` es el registro del entorno, no garantía de instalación universal.
2. Instalar dependencias del archivo raíz `requirements-experiment.in`, preferentemente usando versiones verificadas según el entorno.
3. Ejecutar **solo las verificaciones**, sin entrenamiento: `python -m src.experiments.sidi_run_003_parallel --preflight --report preflight_local.json`.
4. Para entrenar otra vez, utilizar `python -m src.experiments.sidi_run_003_parallel --execute --output-dir experiments/run_003_reproduccion`. **Atención:** SVM probabilístico sobre 96 000 registros consume CPU durante un periodo prolongado.
5. El resultado experimental exporta un *Pipeline* con escalador incorporado, **no compatible directamente** con el consumidor que aplica un escalador separado; no sustituir `models/hybrid_fraud_model.pkl` ni `models/standard_scaler.pkl`.

## Integridad, tamaños y artefactos no publicados en Git

- El CSV principal ya versionado en `data/` se valida con el `contenido_lf_sha256` del manifiesto de SIDI-DATA-002.
- El modelo experimental binario `selected_pipeline.joblib` no se publica en esta carpeta: SHA-256 = `663c5d8d925a08b1deb25d04a2d9222af469ec0313072478ee09a3449a1a7969`. Se conserva en el paquete de evidencias del Paso 4. Es un artefacto `joblib` que debe abrirse únicamente desde una fuente confiable.
- Los CSV con las 19 200 predicciones del test, los índices `.npz`, los checkpoints y los 60 000 registros sintéticos adicionales no se duplican aquí: están en los paquetes de los pasos 4 y 6, y sus resultados agregados están documentados en el repositorio.
- No se versionan `.env`, contraseñas, datos reales de abonados, registros personales ni artefactos temporales. **No hay datos reales de EPS en este repositorio de evidencias.**

## Precauciones de interpretación

- Los 96 000 `cliente_id` son registros sintéticos únicos y los promedios de consumo histórico fueron simulados, no observados.
- Una partición de entrenamiento/test del mismo generador no es validación externa de EPS.
- El procedimiento de estrés usa un generador distinto para explorar escenarios artificiales, **no** para inferir rendimiento en producción.
- `robustez/PROTOCOLO_VALIDACION_EXTERNA_FUTURA.md` es un **protocolo no ejecutado**; requeriría datos reales anonimizados, etiquetas verificadas por expertos y autorizaciones institucionales.
- Esta incorporación se restringe al alcance de la **observación 3**. No modifica los objetivos específicos ni sustituye evidencias de otros componentes.

## Revisión de cambios

Se ha incorporado evidencia en rutas nuevas y scripts de investigación independientes. Los archivos históricos de `run_001`, `run_002`, `data/`, `models/`, `src/1_...`, `src/2_...` y `src/3_model_training.py` se mantienen intactos.
