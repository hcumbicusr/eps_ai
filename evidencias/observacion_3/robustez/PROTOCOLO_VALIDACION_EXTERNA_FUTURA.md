# SIDI — Protocolo de validación externa futura con datos reales de una EPS

**Estado:** PROTOCOLO PROPUESTO; **NO EJECUTADO**. Fecha: 4 de noviembre de 2026.  
**Justificación:** no se dispone actualmente de datos reales, anonimizados ni etiquetados de una empresa prestadora de servicios de saneamiento (EPS). Ningún indicador del paso 4 o paso 6 constituye validación externa real.

## 1. Objetivo de la validación futura

Evaluar de forma independiente, transparente y reproducible el desempeño, la seguridad operativa y la utilidad de un modelo SIDI **congelado** para identificar patrones irregulares del consumo de agua en registros procedentes de una EPS, con etiquetas de referencia verificadas por personal competente. Distinguir entre detección de anomalías de consumo, irregularidades técnicas y fraude corroborado; el último no se deduce automáticamente de la lectura.

## 2. Condiciones previas de inicio

1. **Convenio y permisos:** acuerdo formal con EPS responsable del origen, finalidad, roles, seguridad, retención y destrucción de datos; cumplimiento de normas aplicables de protección de datos y aprobación institucional/ética cuando corresponda.
2. **Datos minimizados:** seudonimizar identificadores, excluir nombres, domicilios y otros identificadores no necesarios del dataset de trabajo; usar transferencias cifradas y acceso controlado, con bitácoras.
3. **Versión congelada:** registrar hash del modelo, versión de código, dependencias, umbral y criterios de aceptación antes de recibir o analizar etiquetas del conjunto externo. Conservar modelo original intacto; si fuera necesario adaptar características, documentar una fase separada y no declarar la evaluación como totalmente externa sin matices.
4. **Diccionario de características:** comprobar disponibilidad y fecha de generación de las 22 variables. Recalcular variables verdaderamente históricas a partir de lecturas de meses anteriores sin mirar el futuro. No recrear artificialmente variables ausentes para forzar comparabilidad.

## 3. Diseño y selección de la cohorte

- Seleccionar un periodo cronológico externo y, cuando sea viable, otra región/EPS no utilizada en entrenamiento. Evitar duplicidad de medidores y contaminación temporal; describir población elegible, exclusiones, estaciones y categorías tarifarias.
- Documentar el mecanismo de selección de registros. Una muestra de **solo inspecciones activadas por SIDI** tendría sesgo de verificación; incluir casos negativos seleccionados independientemente, mediante muestreo definido antes de observar los scores.
- Estimar tamaño muestral según precisión deseada para sensibilidad y tasa esperada de positivos confirmados; no fijar porcentajes de éxito ni afirmar que habrá un número de fraudes. Realizar el cálculo con la EPS antes de recolectar datos.

## 4. Construcción de las etiquetas de referencia

1. Definir operativamente `irregularidad`: desviación medible, error de lectura, fuga, manipulación, fraude confirmado u otra categoría, especificando qué categorías son elegibles como clase 1.
2. Establecer evidencia aceptable por categoría: inspección documentada, prueba técnica, registro de medidor o dictamen administrativo autorizado, evitando equiparar una alerta algorítmica con fraude.
3. Dos revisores especializados, sin acceso a la predicción del modelo cuando sea posible, etiquetan de forma independiente; diferencias se adjudican mediante un tercero o comité y se registra concordancia.
4. Marcar casos ambiguos y definir antes de la evaluación si se excluyen del análisis primario o se reportan por separado; no convertir automáticamente registros sin inspección en negativos.

## 5. Evaluación sin ajuste en el conjunto externo

- Validar esquema, unidades (`m³`, porcentaje decimal), calidad, faltantes, cronología y estabilidad respecto al dataset sintético.
- Ejecutar `predict_proba` del pipeline congelado para todos los registros etiquetados, manteniendo el umbral previamente fijado de 0.50 y sin entrenar ni calibrar usando esta cohorte.
- Reportar matriz VN/FP/FN/VP; precisión, recall/sensibilidad, especificidad, F1, Average Precision, ROC-AUC, tasa de alertas, falsos positivos por 1 000 lecturas e intervalos de confianza adecuados. Reportar también prevalencia y calidad de etiquetas.
- Analizar heterogeneidad por tipo de usuario, sectores, antigüedad del medidor, estaciones y magnitud de anomalía, siempre que el tamaño y protección de datos lo permitan.
- Examinar efectos de selección y verificación diferencial; justificar cualquier ponderación estadística si se utiliza.
- Mantener separadas las estimaciones de exactitud predictiva y las de factibilidad, ahorro o recaudación. Estas últimas requerirán evaluación económica real y supuestos adicionales.

## 6. Criterios de aceptación y decisiones

Los objetivos mínimos de sensibilidad, precisión, tasa de falsos positivos, confianza de etiqueta y carga de inspección deberán negociarse y **prerregistrarse con la EPS** antes de abrir los resultados. No se inventan umbrales aquí. Si se incumplen, registrar limitaciones y no recomendar implementación autónoma; cualquier recalibración/reentrenamiento debe constituir una fase y dataset nuevos con prueba externa reservada posterior.

## 7. Garantías operativas y ética

- El sistema propone **alertas para revisión humana**; la probabilidad del clasificador no demuestra por sí sola fraude ni justifica sanciones o cortes.
- Someter las decisiones a revisión técnica, posibilidad de impugnación, análisis de daños por falsos positivos y procedimiento de auditoría de errores.
- Mantener trazabilidad de versiones, responsables, accesos, criterios de descarte y documentación de incidentes.

## 8. Productos documentales de la futura validación

Convenio/acta de autorización; protocolo firmado y preregistrado; diccionario de variables y diseño de cohorte; bitácora de calidad; procedimiento y actas de etiquetado; dataset desidentificado bajo custodia de la EPS; hashes y versiones; predicciones; matrices y métricas con intervalos; análisis de sesgos; acta de revisión de resultados y recomendaciones de despliegue.

## 9. Situación actual y redacción explícita para la tesis

**Situación actual:** no existen datos reales de EPS ni un proceso externo ejecutado. El estudio aporta evaluación interna del dataset sintético SIDI-DATA-002 y robustez con otros cinco escenarios también sintéticos (SIDI-STRESS-001). La validación externa real se presenta exclusivamente como un procedimiento futuro sujeto al acceso autorizado a datos, etiquetado confiable y aceptación institucional.

**Alcance de subsanación de observación 3:** se cumple la presentación de un *protocolo externo documentado*, pero no la ejecución de una validación real si el jurado la exigiera de forma expresa.
