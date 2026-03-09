import sys
import os
import joblib
import pika
from sqlalchemy import create_engine
from src.config import settings

def run_diagnostics():
    print("=== 🛠️ DIAGNÓSTICO DE SISTEMA EPS-IA ===")
    
    # 1. Validar Librerías Críticas
    try:
        import xgboost
        import pandas
        import sklearn
        print(f"[✅] Librerías de Ciencia de Datos: OK (XGBoost {xgboost.__version__})")
    except ImportError as e:
        print(f"[❌] Error de Librerías: {e}")

    # 2. Validar Conexión a Base de Datos
    try:
        engine = create_engine(settings.get_db_uri())
        with engine.connect() as conn:
            print(f"[✅] Conexión PostgreSQL: OK (Host: {settings.DB_HOST})")
    except Exception as e:
        print(f"[❌] Error PostgreSQL: {e}")

    # 3. Validar Conexión a RabbitMQ
    try:
        credentials = pika.PlainCredentials(settings.RABBIT_USER, settings.RABBIT_PASS)
        params = pika.ConnectionParameters(host=settings.RABBIT_HOST, credentials=credentials)
        connection = pika.BlockingConnection(params)
        print(f"[✅] Conexión RabbitMQ: OK (Host: {settings.RABBIT_HOST})")
        connection.close()
    except Exception as e:
        print(f"[❌] Error RabbitMQ: {e}")

    # 4. Validar Modelos .pkl
    if os.path.exists(settings.MODEL_PATH) and os.path.exists(settings.SCALER_PATH):
        try:
            joblib.load(settings.SCALER_PATH)
            joblib.load(settings.MODEL_PATH)
            print("[✅] Artefactos de IA (.pkl): OK (Cargados en memoria)")
        except Exception as e:
            print(f"[❌] Error al cargar modelos: {e}")
    else:
        print(f"[❌] Error: Archivos .pkl no encontrados en {settings.PROJECT_ROOT}/models/")

if __name__ == "__main__":
    run_diagnostics()