import os
import pandas as pd
from sqlalchemy import create_engine

# 1. Obtiene la carpeta donde reside este script (...\eps_ai\src)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Sube un nivel a la raíz del proyecto (...\eps_ai)
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# 3. Une la ruta apuntando a la carpeta data en la raíz
ruta_csv = os.path.join(PROJECT_ROOT, "data", "dataset_entrenamiento_eps_96000.csv")

def load_data_to_postgres():
    print(f"Buscando archivo en: {ruta_csv}")
    if not os.path.exists(ruta_csv):
        print(f"Error: El archivo no existe en la ruta especificada.")
        return
        
    df = pd.read_csv(ruta_csv)
    
    # 2. Conexión a tu PostgreSQL en Docker (Modifica usuario:password@host:puerto/bd)
    # Ejemplo: postgresql://postgres:root@localhost:5432/eps_db
    engine = create_engine('postgresql://postgres:Admin123@localhost:5433/eps_db')
    
    # 3. Ingesta directa a la base de datos (crea la tabla automáticamente)
    df.to_sql('feature_store_lecturas', engine, if_exists='replace', index=False)
    
    print(f"Éxito: {len(df)} registros insertados en la tabla 'feature_store_lecturas'.")

if __name__ == "__main__":
    load_data_to_postgres()
