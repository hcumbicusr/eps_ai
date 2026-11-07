-- SIDI-PF-001 | Consultas de verificación | 2026-11-06
-- Ejecutar dentro de PostgreSQL eps_db. SOLO LECTURA.
-- Los resultados históricos fueron 101 evaluadas: 46 normales y 55 clase 1;
-- nuevas simulaciones modificarán las cifras.

-- 1. Distribución por estado y clase predicha
SELECT estado_proceso, codigo_prediccion, COUNT(*) AS total
FROM sidi_live.mediciones
GROUP BY estado_proceso, codigo_prediccion
ORDER BY estado_proceso, codigo_prediccion;

-- 2. Conteos de mediciones, clientes, predicciones y fallos
SELECT
    COUNT(*) AS mediciones_total,
    COUNT(DISTINCT cliente_codigo) AS clientes_total,
    COUNT(*) FILTER (WHERE estado_proceso = 'EVALUADA') AS evaluadas_total,
    COUNT(*) FILTER (WHERE codigo_prediccion = 1) AS alertas_total,
    COUNT(*) FILTER (WHERE codigo_prediccion = 0) AS normales_total,
    COUNT(*) FILTER (WHERE estado_proceso = 'SIN_PERFIL') AS sin_perfil_total,
    COUNT(*) FILTER (WHERE estado_proceso = 'ERROR') AS errores_total,
    COUNT(*) FILTER (WHERE estado_proceso = 'RECIBIDA') AS pendientes_total
FROM sidi_live.mediciones;

-- 3. Trazabilidad por lote (solicitudes de simulación frente a registros)
SELECT
    lote_id,
    COUNT(*) AS recibidas,
    COUNT(*) FILTER (WHERE estado_proceso = 'EVALUADA') AS evaluadas,
    COUNT(*) FILTER (WHERE codigo_prediccion = 1) AS alertas
FROM sidi_live.mediciones
GROUP BY lote_id
ORDER BY recibidas DESC;

-- 4. Integridad de la semilla histórica independiente (sin mezclar con live)
SELECT COUNT(*) AS mediciones_demo FROM sidi_demo.mediciones;
