import os
from dotenv import load_dotenv

# Carga el .env (busca en la raíz del proyecto)
load_dotenv()

class Config:
    # --- RabbitMQ ---
    # Coincidiendo con tu .env: RABBIT_USER, RABBIT_PASS, etc.
    RABBIT_USER = os.getenv('RABBIT_USER', 'admin')
    RABBIT_PASS = os.getenv('RABBIT_PASS', 'Admin123')
    RABBIT_HOST = os.getenv('RABBIT_HOST', '127.0.0.1')
    RABBIT_PORT = int(os.getenv('RABBIT_PORT', 5672))
    QUEUE_NAME_MEDICION_REGISTRADA = os.getenv('QUEUE_NAME_MEDICION_REGISTRADA', 'medicion.registrada')

    # --- PostgreSQL ---
    # Coincidiendo con tu .env: DB_USER, DB_PASS, etc.
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASS = os.getenv('DB_PASS', 'Admin123')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432') # Internamente en Docker es 5432
    DB_NAME = os.getenv('DB_NAME', 'eps_db')
    
    # --- Rutas de Archivos ---
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(BASE_DIR)
    
    MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "hybrid_fraud_model.pkl")
    SCALER_PATH = os.path.join(PROJECT_ROOT, "models", "standard_scaler.pkl")
    
    TRAINING_DATASET_FILE = os.getenv('TRAINING_DATASET_FILE', "dataset_entrenamiento_eps_96000.csv")
    PATH_DATASET = os.path.join(PROJECT_ROOT, "data", TRAINING_DATASET_FILE)

    def get_db_uri(self):
        """Genera la URI de conexión dinámicamente."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# Instancia única para ser importada
settings = Config()