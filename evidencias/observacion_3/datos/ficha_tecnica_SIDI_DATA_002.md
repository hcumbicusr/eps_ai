# SIDI – Ficha técnica y consolidación del dataset sintético oficial (Paso 2)

**Proyecto:** Sistema Inteligente de Detección de Irregularidades (SIDI) para empresas prestadoras de servicios de saneamiento (EPS) en Perú  
**Objetivo documental:** responder a la observación 3 con trazabilidad del dataset, generador y variables utilizadas en los experimentos.  
**Fecha de corte:** 4 de noviembre de 2026  
**Identificador de trabajo:** `SIDI-DATA-002` (identificador documental; todavía no es un tag de Git)  
**Commit auditado de `training`:** [`d2cdc2dc`](https://github.com/hcumbicusr/eps_ai/commit/d2cdc2dc120bbb9aef643ac9e6035f179170fc92)

## 1. Decisión de selección
**Se adopta como dataset sintético oficial de referencia** el archivo `data/dataset_entrenamiento_eps_96000.csv`, idéntico en contenido a `run_002/dataset_entrenamiento_eps_96000.csv` según el Git blob del repositorio. El generador asociado es `src/utils/generate_dataset.py`. La adopción significa fijar el insumo de los siguientes pasos; **no certifica la validez de los resultados del entrenamiento anterior ni constituye validación con datos reales**.

**`run_001` queda como antecedente histórico no apto para estimar desempeño principal:** en su dataset, `label = 1` si y solo si `clave_lectura_tipo != 0`, lo que hace trivial la clasificación. No se cuenta con su generador histórico.

## 2. Identidad, volumen y composición

| Control | Resultado comprobado |
|---|---:|
| Filas | 96,000 |
| Variables originales | 27 |
| Variables predictoras | 22 |
| Variables excluidas (incluyendo target) | 5 |
| Clase normal (label=0) | 93,148 |
| Clase irregular simulada (label=1) | 2,852 (2.9708%) |
| Clientes sintéticos únicos | 96,000 |
| Periodo de fechas | 01/01/2025 a 31/12/2025 |
| Valores faltantes | 0 |
| Errores numéricos y fórmulas derivadas revisadas | 0 |

**Unidad de observación:** una lectura sintética asociada a un `cliente_id` sintético y una fecha simulada. En este CSV no hay más de una lectura por cliente. Las variables llamadas “históricas” son parámetros artificialmente generados.

## 3. Procedencia y generación

- El generador establece `NUM_REGISTROS=96000`, `PCT_FRAUDE=0.03` y `np.random.seed(42)`. La tasa efectiva de `label=1` resulta 2.9708%, no exactamente 3%, debido al sorteo aleatorio.
- Primero sortea la etiqueta de cada registro; después genera el consumo base y, para los etiquetados como irregulares, impone reducciones o picos simulados. No se observaron irregularidades de una EPS ni se validaron con inspecciones.
- `tiene_reclamo` se construye condicionado por la etiqueta y `reclamo_favor_cliente` depende de `tiene_reclamo`. El preprocesamiento excluye ambas variables, además de ID, fecha y etiqueta.
- El generador fue reproducido de manera aislada en el paso 1, con coincidencia exacta del CSV tras normalización de finales de línea LF/CRLF. Esto valida la **reproducibilidad del dataset**, no la de los modelos.

## 4. Diccionario de variables (27 campos)

El archivo XLSX adjunto contiene un diccionario completo con tipo, rango observado, definición operativa, algoritmo de generación, unidad, rol en el modelo y advertencia de interpretación para cada columna.

| N.º | Variable | Rol | Orden en modelo | Descripción breve |
|---:|---|---|---:|---|
| 1 | `cliente_id` | Excluida | — | Identificador único sintético del registro/cliente. |
| 2 | `timestamp_medicion` | Excluida | — | Fecha asignada a la medición sintética. |
| 3 | `mes_escalar` | Predictora | 1 | Mes calendario de la medición. |
| 4 | `contexto_estacional` | Predictora | 2 | Código estacional simplificado para la simulación. |
| 5 | `es_fin_de_semana` | Predictora | 3 | Indica si la fecha cae en sábado o domingo. |
| 6 | `es_mes_festivo` | Predictora | 4 | Indicador sintético de meses elegidos como festivos. |
| 7 | `clase_servicio` | Predictora | 5 | Código sintético de clase de servicio. |
| 8 | `categoria_tarifaria` | Predictora | 6 | Código sintético de categoría tarifaria. |
| 9 | `consumo_m3` | Predictora | 7 | Lectura/consumo actual simulado. |
| 10 | `dias_entre_lecturas` | Predictora | 8 | Número simulado de días entre lecturas. |
| 11 | `lectura_estimada_flag` | Predictora | 9 | Indicador de lectura estimada simulada. |
| 12 | `clave_lectura_tipo` | Predictora | 10 | Código sintético del tipo de lectura. |
| 13 | `antiguedad_medidor_meses` | Predictora | 11 | Antigüedad simulada del medidor. |
| 14 | `mora_dias` | Predictora | 12 | Días simulados de mora. |
| 15 | `tiene_deuda_activa` | Predictora | 13 | Indicador de deuda derivado de la mora. |
| 16 | `avg_consumo_6m` | Predictora | 14 | Promedio nominal de consumo histórico sintético. |
| 17 | `std_consumo_6m` | Predictora | 15 | Desviación estándar nominal del consumo histórico sintético. |
| 18 | `var_pct_mes` | Predictora | 16 | Variación relativa del consumo actual frente al promedio nominal. |
| 19 | `ceros_ult12` | Predictora | 17 | Conteo nominal de lecturas con cero en los últimos 12 periodos. |
| 20 | `temperatura_maxima` | Predictora | 18 | Temperatura máxima nominal simulada. |
| 21 | `precipitacion_acumulada` | Predictora | 19 | Precipitación acumulada nominal simulada. |
| 22 | `sector_riesgo_0_1` | Predictora | 20 | Indicador nominal de riesgo de sector sintético. |
| 23 | `cluster_eps_id` | Predictora | 21 | Identificador sintético de conglomerado EPS. |
| 24 | `perfil_cluster_kmeans` | Predictora | 22 | Código de perfil de clúster sintético. |
| 25 | `tiene_reclamo` | Excluida | — | Indicador sintético de reclamo. |
| 26 | `reclamo_favor_cliente` | Excluida | — | Indicador sintético de resolución favorable. |
| 27 | `label` | Objetivo | — | Clase objetivo de irregularidad simulada. |

### Diferencia entre las 27 columnas y las 22 características predictoras
Las cinco columnas excluidas por `src/2_model_preprocessing.py` son: `cliente_id`, `timestamp_medicion`, `tiene_reclamo`, `reclamo_favor_cliente` y `label` (esta última es el objetivo). Así: **27 − 5 = 22** variables predictoras.

**Orden exacto de entrada al modelo (debe conservarse en entrenamiento e inferencia):**

1. `mes_escalar`
2. `contexto_estacional`
3. `es_fin_de_semana`
4. `es_mes_festivo`
5. `clase_servicio`
6. `categoria_tarifaria`
7. `consumo_m3`
8. `dias_entre_lecturas`
9. `lectura_estimada_flag`
10. `clave_lectura_tipo`
11. `antiguedad_medidor_meses`
12. `mora_dias`
13. `tiene_deuda_activa`
14. `avg_consumo_6m`
15. `std_consumo_6m`
16. `var_pct_mes`
17. `ceros_ult12`
18. `temperatura_maxima`
19. `precipitacion_acumulada`
20. `sector_riesgo_0_1`
21. `cluster_eps_id`
22. `perfil_cluster_kmeans`

## 5. Controles de integridad y calidad

En el paso 2 se revisaron todas las filas del CSV mediante lectura programática. Se verificó que no existen valores faltantes, que las variables numéricas son finitas, que las fechas son válidas, que los IDs son únicos y que coinciden las fórmulas de `mes_escalar`, `contexto_estacional`, `es_fin_de_semana`, `es_mes_festivo`, `tiene_deuda_activa` y `var_pct_mes`. También se verificó que `reclamo_favor_cliente=1` solo aparece cuando `tiene_reclamo=1`. Todos estos controles registraron cero inconsistencias.

**No equivale a verificar plausibilidad real:** un valor consistente con el generador puede no ser realista para una EPS; la simulación no demuestra calidad de datos de campo.

## 6. Huellas criptográficas y trazabilidad Git

| Objeto | Hash |
|---|---|
| CSV adjunto original (SHA-256, CRLF) | `5b3bf2a72a76479e7ff829130080445f62d6f174a4a0621edaf90bdbc6ee4803` |
| Mismo contenido normalizado a LF (SHA-256) | `a26191fbca07a518ed73715d714ed8c6619c4caa1a65637658945e5a0784f25c` |
| Git blob SHA-1 del CSV normalizado | `4669b99bb14de6e1aa0e69a1aad245deca12f776` |
| Generador `generate_dataset.py` (Git blob SHA-1) | `7e7c3866cf85e638eb023e9c847f9321c707569d` |
| Generador normalizado a LF (SHA-256) | `2b86ec59d555b52762a48c5d96c19a1cab8e239badd60f3e395e7f524a8be03e` |
| Commit de referencia | `d2cdc2dc120bbb9aef643ac9e6035f179170fc92` |

Los archivos CSV y generador adjuntos tienen finales de línea `CRLF`; las versiones correspondientes en Git usan `LF`. El contenido es equivalente al normalizar solamente los finales de línea. Los SHA-256 anteriores describen **representaciones de bytes distintas** de ese mismo contenido; no son intercambiables.

Fuentes versionadas:
- [Dataset principal en GitHub](https://github.com/hcumbicusr/eps_ai/blob/d2cdc2dc120bbb9aef643ac9e6035f179170fc92/data/dataset_entrenamiento_eps_96000.csv)
- [Copia inmutable del experimento run_002 (en el commit auditado)](https://github.com/hcumbicusr/eps_ai/blob/d2cdc2dc120bbb9aef643ac9e6035f179170fc92/run_002/dataset_entrenamiento_eps_96000.csv)
- [Generador en GitHub](https://github.com/hcumbicusr/eps_ai/blob/d2cdc2dc120bbb9aef643ac9e6035f179170fc92/src/utils/generate_dataset.py)
- [Selección de 22 variables en preprocesamiento](https://github.com/hcumbicusr/eps_ai/blob/d2cdc2dc120bbb9aef643ac9e6035f179170fc92/src/2_model_preprocessing.py)

## 7. Limitaciones que deben declararse en la tesis

1. **Ausencia de datos reales:** no existe dataset EPS real ni validación externa ejecutada. Los resultados deben limitarse al entorno sintético.
2. **Etiquetas construidas por simulación:** `label` antecede a la creación de las anomalías de consumo. No debe interpretarse como fraude constatado.
3. **No hay historial longitudinal por cliente:** cada `cliente_id` aparece una vez; `avg_consumo_6m`, `std_consumo_6m` y `ceros_ult12` no proceden de observaciones previas.
4. **No hay clústeres aprendidos:** `perfil_cluster_kmeans` es aleatorio y `cluster_eps_id` tampoco identifica EPS reales.
5. **Contexto artificial:** clima y riesgo sectorial no están emparejados con fuentes externas; categorías de servicio y códigos tarifarios no tienen correspondencia documentada con un catálogo EPS.
6. **Escala de la variación:** `var_pct_mes` se almacena como proporción decimal (`0.5` significa 50%), pese a que su nombre diga “pct”.
7. **Modelo aún por corregir:** los resultados de `run_002` son históricos; se debe corregir la validación cruzada antes de producir la evidencia final.
8. **Procedencia de la tabla SQL:** la corrida histórica no incluye un hash verificable de la tabla PostgreSQL leída; habrá que registrar esta vinculación en el protocolo corregido.

## 8. Texto metodológico propuesto para insertar en la tesis

> Para la evaluación experimental del componente de inteligencia artificial del SIDI se empleó un conjunto de datos completamente sintético de 96,000 registros y 27 variables, generado mediante un procedimiento reproducible implementado en Python con semilla aleatoria 42. El conjunto comprende 93,148 observaciones etiquetadas como normales (97.03%) y 2,852 observaciones de irregularidad simulada (2.97%). La etiqueta fue definida dentro del proceso de simulación y utilizada para introducir alteraciones artificiales en el consumo, por lo que no corresponde a casos reales verificados por una EPS. Después de excluir identificador, fecha, variables de reclamos vinculadas a la etiqueta y columna objetivo, se conservan 22 características predictoras. Los resultados obtenidos a partir de este conjunto solo permiten evaluar el comportamiento del sistema en escenarios sintéticos y no acreditan su desempeño en condiciones operativas reales. La validación externa con datos históricos de una EPS queda definida como una etapa futura, sujeta a disponibilidad y autorización de datos.

**Nota:** este texto de metodología describe el dataset; las métricas de un nuevo entrenamiento definitivo deberán añadirse solo después de ejecutar los pasos 3 a 5.

## 9. Estado y límites del paso 2

**Terminado:** selección documental del dataset `run_002`, diccionario de 27 variables, orden de 22 entradas al modelo, verificaciones de calidad y manifiesto de integridad.  
**No ejecutado:** modificación del generador, dataset, base PostgreSQL o repositorio; entrenamiento de modelos; correcciones del pipeline; validación de campo.  
**Próximo paso (requiere GO):** Paso 3, corrección del pipeline de entrenamiento y definición del protocolo experimental final.

