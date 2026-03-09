import os
import pandas as pd
from sqlalchemy import create_engine
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
from src.config import settings
from src.utils.logger_setup import setup_logger
# Se activa el log automáticamente
setup_logger("model_preprocessing")

def extract_and_preprocess():
    print("Extrayendo datos desde PostgreSQL...")
    engine = create_engine(settings.get_db_uri())
    
    # Consulta SQL para extraer el dataset
    query = "SELECT * FROM feature_store_lecturas ORDER BY timestamp_medicion"
    df = pd.read_sql(query, engine)
    
    # 1. Selección de Características (Feature Selection)
    # Eliminamos variables que no son predictivas (ID) o que generan fuga de información (data leakage).
    # 'reclamo_favor_cliente' se excluye porque ocurre DESPUÉS de la lectura.
    columnas_excluir = ['cliente_id', 'timestamp_medicion', 'tiene_reclamo', 'reclamo_favor_cliente', 'label']
    
    X = df.drop(columns=columnas_excluir)
    y = df['label'] # Nuestro Target (0 = Normal, 1 = Irregular)
    
    # 2. División de Datos (80% Entrenamiento, 20% Validación/Prueba)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"Dimensión de Entrenamiento: {X_train.shape}")
    print(f"Dimensión de Prueba: {X_test.shape}")
    
    # 3. Escalado de Características (StandardScaler)
    # Crucial para Redes Neuronales y útil para algoritmos basados en árboles
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 4. Serialización de objetos intermedios para la API (FastAPI)
    joblib.dump(scaler, os.path.join(settings.PROJECT_ROOT, "models", "standard_scaler.pkl"))
    print("Escalador guardado en /models.")
    
    return X_train_scaled, X_test_scaled, y_train, y_test, X.columns

if __name__ == "__main__":
    X_train, X_test, y_train, y_test, features = extract_and_preprocess()
    print("Preprocesamiento finalizado. Escalador guardado en /models.")
