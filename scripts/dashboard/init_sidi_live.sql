-- Registros procesados por RabbitMQ y el modelo IA. Independiente de sidi_demo y entrenamiento.
BEGIN;
CREATE SCHEMA IF NOT EXISTS sidi_live;
CREATE TABLE IF NOT EXISTS sidi_live.mediciones (
    evento_id UUID PRIMARY KEY,
    lote_id UUID,
    cliente_codigo VARCHAR(30) NOT NULL,
    fecha_lectura TIMESTAMPTZ NOT NULL,
    fecha_recepcion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    consumo_m3 NUMERIC(12,2) NOT NULL CHECK (consumo_m3 >= 0),
    lectura_estimada BOOLEAN NOT NULL DEFAULT FALSE,
    sector VARCHAR(50) NOT NULL DEFAULT 'Sin perfil',
    origen VARCHAR(20) NOT NULL DEFAULT 'ingesta',
    estado_proceso VARCHAR(20) NOT NULL DEFAULT 'RECIBIDA'
        CHECK (estado_proceso IN ('RECIBIDA','EVALUADA','SIN_PERFIL','ERROR')),
    codigo_prediccion SMALLINT CHECK (codigo_prediccion IN (0,1)),
    score_irregular_pct NUMERIC(5,2) CHECK (score_irregular_pct BETWEEN 0 AND 100),
    estado_revision VARCHAR(40),
    detalle_error VARCHAR(250),
    procesado_en TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sidi_live_fecha ON sidi_live.mediciones(fecha_recepcion DESC);
CREATE INDEX IF NOT EXISTS idx_sidi_live_lote ON sidi_live.mediciones(lote_id);
CREATE INDEX IF NOT EXISTS idx_sidi_live_sector ON sidi_live.mediciones(sector);
CREATE INDEX IF NOT EXISTS idx_sidi_live_proceso ON sidi_live.mediciones(estado_proceso, codigo_prediccion);
COMMIT;
