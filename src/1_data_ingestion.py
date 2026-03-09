import os
import pandas as pd
from sqlalchemy import create_engine
from src.config import settings  # Importamos la configuración centralizada
from src.utils.logger_setup import setup_logger
# Se activa el log automáticamente
setup_logger("data_ingestion")

# 3. Une la ruta apuntando a la carpeta data en la raíz
ruta_csv = settings.PATH_DATASET  # Esto ya incluye la ruta completa al dataset

def load_data_to_postgres():
    print(f"Buscando archivo en: {ruta_csv}")
    if not os.path.exists(ruta_csv):
        print(f"Error: El archivo no existe en la ruta especificada.")
        return
        
    df = pd.read_csv(ruta_csv)
    
    # 2. Conexión a tu PostgreSQL en Docker (Modifica usuario:password@host:puerto/bd)
    # Ejemplo: postgresql://postgres:root@localhost:5432/eps_db
    engine = create_engine(settings.get_db_uri())
    
    # 3. Ingesta directa a la base de datos (crea la tabla automáticamente)
    df.to_sql('feature_store_lecturas', engine, if_exists='replace', index=False)
    
    print(f"Éxito: {len(df)} registros insertados en la tabla 'feature_store_lecturas'.")

if __name__ == "__main__":
    load_data_to_postgres()
