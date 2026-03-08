import os
import sys
import time
import joblib
import warnings
import numpy as np
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# =====================================================================
# CONFIGURACIÓN DE RUTAS Y LOGGING REAL-TIME
# =====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d")
log_filename = os.path.join(LOGS_DIR, f"log_fastapi_{timestamp}.log")

class RealTimeLogger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush() # <--- Crucial para escritura en tiempo real

    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = RealTimeLogger(log_filename)
warnings.filterwarnings('ignore')

# =====================================================================
# INICIALIZACIÓN Y CARGA DE MODELOS
# =====================================================================
app = FastAPI(title="Servicio IA - EPS Detección de Fraude", version="1.0.0")

# Rutas absolutas para evitar fallos de carga
SCALER_PATH = os.path.join(PROJECT_ROOT, "models", "standard_scaler.pkl")
MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "hybrid_fraud_model.pkl")

print(f"[{datetime.now()}] [SISTEMA] Cargando artefactos desde: {PROJECT_ROOT}")

try:
    scaler = joblib.load(SCALER_PATH)
    model = joblib.load(MODEL_PATH)
    print(f"[{datetime.now()}] [ÉXITO] Modelos en RAM. API lista.")
except Exception as e:
    print(f"[{datetime.now()}] [ERROR CRÍTICO] Fallo al cargar .pkl: {e}")

# =====================================================================
# MIDDLEWARE PARA LOGS DE PETICIONES
# =====================================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    
    # Registro en tiempo real de cada hit a la API
    print(f"[{datetime.now()}] {request.method} {request.url.path} | "
          f"Status: {response.status_code} | Latencia: {process_time:.2f}ms")
    return response

# =====================================================================
# ESQUEMA Y ENDPOINTS
# =====================================================================
class LecturaMedidor(BaseModel):
    mes_escalar: int
    contexto_estacional: int
    es_fin_de_semana: int
    es_mes_festivo: int
    clase_servicio: int
    categoria_tarifaria: int
    consumo_m3: float
    dias_entre_lecturas: int
    lectura_estimada_flag: int
    clave_lectura_tipo: int
    antiguedad_medidor_meses: int
    mora_dias: int
    tiene_deuda_activa: int
    avg_consumo_6m: float
    std_consumo_6m: float
    var_pct_mes: float
    ceros_ult12: float
    temperatura_maxima: float
    precipitacion_acumulada: float
    sector_riesgo_0_1: float
    cluster_eps_id: int
    perfil_cluster_kmeans: int

@app.post("/predict")
async def evaluar_lectura(lectura: LecturaMedidor):
    try:
        data_dict = lectura.dict()
        input_data = np.array([list(data_dict.values())])

        # Inferencia
        input_scaled = scaler.transform(input_data)
        prediccion_clase = model.predict(input_scaled)[0]
        probabilidades = model.predict_proba(input_scaled)[0]
        
        # Clase 1 es Fraude (índice 1 en predict_proba)
        riesgo_fraude_pct = round(float(probabilidades[1]) * 100, 2)

        estado = "Irregular / Fraude Detectado" if prediccion_clase == 1 else "Consumo Normal"
        accion = "Programar Inspección (VAI01A)" if prediccion_clase == 1 else "Aprobar Facturación"

        resultado = {
            "estado_evaluacion": estado,
            "riesgo_fraude_porcentaje": riesgo_fraude_pct,
            "codigo_prediccion": int(prediccion_clase),
            "accion_sugerida": accion
        }
        
        # Log del resultado específico
        print(f" > PREDICCIÓN: {estado} (Riesgo: {riesgo_fraude_pct}%)")
        return resultado

    except Exception as e:
        print(f"[{datetime.now()}] [ERROR INFERENCIA]: {str(e)}")
        raise HTTPException(status_code=500, detail="Error en el procesamiento de datos.")

@app.get("/health")
async def health_check():
    return {"status": "online", "timestamp": datetime.now()}