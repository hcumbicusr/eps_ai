-- SIDI / DATOS 100 % SINTÉTICOS PARA DEMOSTRACIÓN
-- Esquema independiente: no altera feature_store_lecturas ni alertas_irregularidades.
-- Repetir este archivo NO duplica registros: IDs estables + ON CONFLICT DO NOTHING.
BEGIN;
CREATE SCHEMA IF NOT EXISTS sidi_demo;
CREATE TABLE IF NOT EXISTS sidi_demo.mediciones (
  id INTEGER PRIMARY KEY,
  cliente_codigo VARCHAR(30) NOT NULL,
  fecha_lectura DATE NOT NULL,
  sector VARCHAR(40) NOT NULL,
  consumo_m3 NUMERIC(9,2) NOT NULL CHECK (consumo_m3 >= 0),
  lectura_estimada BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS sidi_demo.alertas (
  id INTEGER PRIMARY KEY,
  medicion_id INTEGER NOT NULL UNIQUE REFERENCES sidi_demo.mediciones(id),
  fecha DATE NOT NULL,
  tipo VARCHAR(80) NOT NULL,
  score_pct NUMERIC(5,2) NOT NULL CHECK (score_pct BETWEEN 0 AND 100),
  estado VARCHAR(40) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sidi_demo_mediciones_fecha ON sidi_demo.mediciones(fecha_lectura);
CREATE INDEX IF NOT EXISTS ix_sidi_demo_mediciones_sector ON sidi_demo.mediciones(sector);
CREATE INDEX IF NOT EXISTS ix_sidi_demo_alertas_estado ON sidi_demo.alertas(estado);

-- 5 984 lecturas de 1 200 clientes ficticios, distribuidas por meses y sectores.
INSERT INTO sidi_demo.mediciones(id, cliente_codigo, fecha_lectura, sector, consumo_m3, lectura_estimada)
SELECT n,
       'DEMO-' || lpad((((n - 1) % 1200) + 1)::text, 5, '0'),
       DATE '2025-01-01' + (((n - 1) * 37) % 365),
       'Sector A' || ((((n - 1) / 13) % 4) + 1)::text,
       (8 + ((n * 17) % 510) / 10.0)::numeric(9,2),
       n % 11 = 0
FROM generate_series(1, 5984) AS n
ON CONFLICT (id) DO NOTHING;

-- 9 alertas DEMO, con distintos sectores, estados y tipologías.
WITH seeds(id, medicion_id, tipo, score_pct, estado) AS (
 VALUES
  (1, 15, 'Variación atípica', 92.40, 'PENDIENTE_CAMPO'),
  (2, 520, 'Lectura inusual', 86.20, 'EN_REVISION'),
  (3, 1033, 'Variación atípica', 78.30, 'CERRADO'),
  (4, 1521, 'Consumo elevado', 90.15, 'PENDIENTE_CAMPO'),
  (5, 2077, 'Consumo elevado', 74.90, 'EN_REVISION'),
  (6, 3008, 'Lectura inusual', 88.55, 'PENDIENTE_CAMPO'),
  (7, 4046, 'Variación atípica', 84.10, 'CERRADO'),
  (8, 5120, 'Consumo elevado', 79.35, 'PENDIENTE_CAMPO'),
  (9, 5922, 'Lectura inusual', 95.60, 'EN_REVISION')
)
INSERT INTO sidi_demo.alertas(id, medicion_id, fecha, tipo, score_pct, estado)
SELECT s.id, s.medicion_id, m.fecha_lectura, s.tipo, s.score_pct, s.estado
FROM seeds s JOIN sidi_demo.mediciones m ON m.id = s.medicion_id
ON CONFLICT (id) DO NOTHING;
COMMIT;
