"""Asegura perfiles para C00000..C00099 sin vaciar clientes existentes.

Lee atributos del dataset sintético versionado. ON CONFLICT DO NOTHING preserva
cualquier perfil previamente registrado (sin TRUNCATE).
"""
import csv
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'data' / os.getenv('TRAINING_DATASET_FILE', 'dataset_entrenamiento_eps_96000.csv')
FIELDS = (
    'cliente_id', 'clase_servicio', 'categoria_tarifaria', 'antiguedad_medidor_meses',
    'mora_dias', 'tiene_deuda_activa', 'avg_consumo_6m', 'std_consumo_6m',
    'ceros_ult12', 'sector_riesgo_0_1', 'cluster_eps_id', 'perfil_cluster_kmeans',
    'temperatura_maxima', 'precipitacion_acumulada'
)


def main() -> None:
    if not SOURCE.is_file():
        raise RuntimeError(f'Dataset sintético no encontrado: {SOURCE}')
    profiles = {}
    with SOURCE.open(encoding='utf-8-sig', newline='') as fp:
        for record in csv.DictReader(fp):
            name = record['cliente_id']
            if name in {f'C{i:05d}' for i in range(100)} and name not in profiles:
                profiles[name] = {k: record[k] for k in FIELDS}
                if len(profiles) == 100:
                    break
    if len(profiles) != 100:
        raise RuntimeError(f'Se requieren 100 perfiles C00000-C00099; hallados {len(profiles)}')

    url = URL.create('postgresql+psycopg2', username=os.getenv('DB_USER','postgres'),
                     password=os.getenv('DB_PASS',''), host=os.getenv('DB_HOST','postgres-eps-db'),
                     port=int(os.getenv('DB_PORT','5432')), database=os.getenv('DB_NAME','eps_db'))
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS cliente_features (
                codigo_cliente VARCHAR(20) PRIMARY KEY,
                clase_servicio INTEGER,
                categoria_tarifaria INTEGER,
                antiguedad_medidor_meses INTEGER,
                mora_dias INTEGER,
                tiene_deuda_activa INTEGER,
                avg_consumo_6m NUMERIC,
                std_consumo_6m NUMERIC,
                ceros_ult12 NUMERIC,
                sector_riesgo_0_1 NUMERIC,
                cluster_eps_id INTEGER,
                perfil_cluster_kmeans INTEGER,
                temperatura_maxima NUMERIC,
                precipitacion_acumulada NUMERIC
            )
        '''))
        for record in profiles.values():
            conn.execute(text('''
                INSERT INTO cliente_features (
                    codigo_cliente, clase_servicio, categoria_tarifaria, antiguedad_medidor_meses,
                    mora_dias, tiene_deuda_activa, avg_consumo_6m, std_consumo_6m,
                    ceros_ult12, sector_riesgo_0_1, cluster_eps_id, perfil_cluster_kmeans,
                    temperatura_maxima, precipitacion_acumulada
                ) VALUES (
                    :cliente_id, :clase_servicio, :categoria_tarifaria, :antiguedad_medidor_meses,
                    :mora_dias, :tiene_deuda_activa, :avg_consumo_6m, :std_consumo_6m,
                    :ceros_ult12, :sector_riesgo_0_1, :cluster_eps_id, :perfil_cluster_kmeans,
                    :temperatura_maxima, :precipitacion_acumulada
                ) ON CONFLICT(codigo_cliente) DO NOTHING
            '''), record)
        count = conn.execute(text("SELECT count(*) FROM cliente_features WHERE codigo_cliente LIKE 'C000%' AND length(codigo_cliente)=6")).scalar_one()
    print(f'Perfiles sintéticos de simulación preparados; perfiles C000xx presentes: {count}')


if __name__ == '__main__':
    main()
