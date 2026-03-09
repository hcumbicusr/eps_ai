import os
import sys
from datetime import datetime
import warnings
from src.config import settings # Importamos tu configuración centralizada

class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush() # Escritura en tiempo real

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def setup_logger(service_name="app"):
    """
    Configura el logger dinámicamente. 
    service_name: Prefijo para el archivo (ej: 'training', 'consumer', 'api')
    """
    # Usar PROJECT_ROOT desde settings
    logs_dir = os.path.join(settings.PROJECT_ROOT, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d")
    log_filename = os.path.join(logs_dir, f"log_{service_name}_{timestamp}.log")

    # Redirigir stdout
    sys.stdout = Logger(log_filename)
    warnings.filterwarnings('ignore')
    
    print(f"--- LOGGER INICIADO: {service_name.upper()} ---")
    print(f"Archivo: {log_filename}")
    return log_filename