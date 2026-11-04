# SIDI-RUN-003 — Evidencia y reproducción del Paso 4

Este paquete NO contiene el dataset original por duplicación y tamaño: se obtiene de la rama `training` en `hcumbicusr/eps_ai`, archivo `data/dataset_entrenamiento_eps_96000.csv`. **No se enviaron cambios a GitHub**.

## Archivos en el ZIP

- `experiments/run_003/`: resultados completos, modelo `.joblib`, logs, scores por fold, índices y configuraciones.
- `src/experiments/sidi_run_003.py`: protocolo original diseñado en Paso 3 (secuencial).
- `src/experiments/sidi_run_003_parallel.py`: implementación equivalente en paralelo efectivamente ejecutada.
- `protocolos/`: copia de configuración y manifiesto del dataset.
- `tests/`: 8 pruebas de integridad, particiones y equivalencia de soft voting.
- `verificacion_evidencias_RUN_003.json` y `smoke_modelo_entrenado.json`: QA del experimento.
- `INFORME_CIERRE_PASO_4.md`: resumen factual, sin interpretación del Paso 5.
- `interrupcion_secuencial/`: log de intento inicial interrumpido por costo computacional (no mezclar con resultados definitivos).

## Reproducir en un clon del repositorio

1. Clonar `https://github.com/hcumbicusr/eps_ai` y seleccionar la rama `training` (`git checkout training`). Idealmente fijar el commit `d2cdc2dc120bbb9aef643ac9e6035f179170fc92`.
2. Copiar `src/experiments/`, `protocolos/` y `tests/` del ZIP al clon; **no** reemplazar `src/3_model_training.py` o artefactos en `models/`.
3. Preparar un entorno Python con las versiones de `experiments/run_003/requirements_freeze.txt`; en plataformas diferentes puede ser necesario resolver dependencias compatibles. Entorno verificado: Python 3.13.5.
4. Ejecutar desde raíz:

   `python -m src.experiments.sidi_run_003_parallel --preflight --report preflight_reproducido.json`

5. Para reproducir completamente, usar una carpeta **nueva** y no sobrescribir evidencias:

   `python -m src.experiments.sidi_run_003_parallel --execute --output-dir experiments/run_003_reproduccion`

6. Comparar las tablas CV, el modelo seleccionado y las métricas de test con los archivos proporcionados. Dependiendo de la arquitectura y las versiones de librerías, puede haber pequeñas variaciones numéricas; cualquier discrepancia debe documentarse.

**Precaución estadística:** no usar la evaluación reservada ya conocida para cambiar parámetros ni seleccionar modelos después de esta corrida; una decisión diferente requeriría un protocolo nuevo y un test independiente.

**Precaución despliegue:** este artefacto incluye `StandardScaler` internamente y no es directamente intercambiable con el modelo actual que recibe características ya escaladas.
