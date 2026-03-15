import pandas as pd
from sqlalchemy import create_engine, text
from src.config import settings
from src.utils.logger_setup import setup_logger

setup_logger("populate_features")

def poblar_feature_store():
    engine = create_engine(settings.get_db_uri())
    
    print("[1/4] Configurando estructura de tabla...")
    with engine.connect() as conn:
        # Usamos text() para compatibilidad con SQLAlchemy 2.0
        conn.execute(text("""
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
            );
        """))
        # Opcional: Limpiar datos previos si quieres una carga fresca
        conn.execute(text("TRUNCATE TABLE cliente_features;"))
        conn.commit() # Asegurar que los cambios se guarden

    print(f"[2/4] Leyendo dataset desde: {settings.PATH_DATASET}")
    df = pd.read_csv(settings.PATH_DATASET)
    
    # Procesamiento de datos
    df['timestamp_medicion'] = pd.to_datetime(df['timestamp_medicion'])
    df_latest = df.sort_values('timestamp_medicion').drop_duplicates('cliente_id', keep='last')
    
    columnas_map = {
        'cliente_id': 'codigo_cliente',
        'clase_servicio': 'clase_servicio',
        'categoria_tarifaria': 'categoria_tarifaria', 
        'antiguedad_medidor_meses': 'antiguedad_medidor_meses',
        'mora_dias': 'mora_dias',
        'tiene_deuda_activa': 'tiene_deuda_activa',
        'avg_consumo_6m': 'avg_consumo_6m',
        'std_consumo_6m': 'std_consumo_6m',
        'ceros_ult12': 'ceros_ult12', 
        'sector_riesgo_0_1': 'sector_riesgo_0_1',
        'cluster_eps_id': 'cluster_eps_id',
        'perfil_cluster_kmeans': 'perfil_cluster_kmeans',
        'temperatura_maxima': 'temperatura_maxima',
        'precipitacion_acumulada': 'precipitacion_acumulada'
    }
    
    df_features = df_latest[list(columnas_map.keys())].copy()
    df_features.rename(columns=columnas_map, inplace=True)
    
    print(f"[3/4] Insertando {len(df_features)} perfiles en PostgreSQL...")
    
    # Usamos append porque la tabla ya existe con su PK y estructura correcta
    df_features.to_sql(
        'cliente_features', 
        engine, 
        if_exists='append', 
        index=False,
        method='multi', # Acelera la inserción por lotes
        chunksize=1000  # Evita saturar la memoria en cargas grandes
    )
    
    print("[4/4] [ÉXITO] Feature Store poblado y listo para inferencia.")

if __name__ == "__main__":
    poblar_feature_store()