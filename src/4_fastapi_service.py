import time
import joblib
import numpy as np
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from src.config import settings
from src.utils.logger_setup import setup_logger
# Se activa el log automáticamente
setup_logger("fastapi_service")

app = FastAPI(
    title="Servicio IA - EPS Detección de Patrones Irregulares", 
    version="1.0.0",
    description="API de inferencia para detección de irregularidades en consumos de agua"
)

# =====================================================================
# CARGA DE ARTEFACTOS CENTRALIZADA
# =====================================================================
print(f"[SISTEMA] Cargando artefactos desde: {settings.PROJECT_ROOT}")

try:
    # Usamos las rutas ya validadas en settings
    scaler = joblib.load(settings.SCALER_PATH)
    model = joblib.load(settings.MODEL_PATH)
    print(f"[ÉXITO] Modelos en RAM. API lista para inferencia.")
except Exception as e:
    # Este error ahora también se escribirá en el archivo .log
    print(f"[ERROR CRÍTICO] Fallo al cargar artefactos .pkl: {e}")
    # En producción, podrías querer detener el proceso aquí

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
            "riesgo_irregularidad_porcentaje": riesgo_fraude_pct,
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