import os
import sys
import time
import pika
import json
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
import warnings
from datetime import datetime

# =====================================================================
# CONFIGURACIÓN DE RUTAS Y LOGGING REAL-TIME
# =====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Log por día para evitar archivos gigantescos
timestamp_file = datetime.now().strftime("%Y%m%d")
log_filename = os.path.join(LOGS_DIR, f"worker_ia_{timestamp_file}.log")

class RealTimeLogger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        # Agregamos timestamp a cada línea que no sea un salto de línea vacío
        if message.strip():
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f"[{now}] {message}"
        else:
            formatted_message = message
            
        self.terminal.write(formatted_message)
        self.log.write(formatted_message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = RealTimeLogger(log_filename)
warnings.filterwarnings('ignore')

# ==============================================================================
# CONFIGURACIÓN DE ARQUITECTURA
# ==============================================================================
RABBITMQ_HOST = 'localhost'
QUEUE_NAME = 'medicion.registrada'
DB_URI = 'postgresql://postgres:Admin123@localhost:5433/eps_db' 

print(" [SISTEMA] Iniciando Motor de Inferencia IA...")

try:
    SCALER_PATH = os.path.join(PROJECT_ROOT, "models", "standard_scaler.pkl")
    MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "hybrid_fraud_model.pkl")
    
    scaler = joblib.load(SCALER_PATH)
    model = joblib.load(MODEL_PATH)
    engine = create_engine(DB_URI)
    print(" [ÉXITO] Componentes cargados. Conexión a DB establecida.")
except Exception as e:
    print(f" [ERROR CRÍTICO] No se pudo iniciar el worker: {e}")
    sys.exit(1)

# ==============================================================================
# LÓGICA DE PROCESAMIENTO
# ==============================================================================
def procesar_medicion(ch, method, properties, body):
    try:
        message = json.loads(body)
        print(f" [📥 EVENTO] Mensaje recibido: {message}")
        data = message.get('data', {})
        print(f" [📥 EVENTO] Procesando lectura de Cluster: {data.get('cluster_eps_id')} | Consumo: {data.get('consumo_m3')} m3")
        
        # Construcción del vector de entrada (22 features)
        features = np.array([[
            data['mes_escalar'], data['contexto_estacional'], data['es_fin_de_semana'],
            data['es_mes_festivo'], data['clase_servicio'], data['categoria_tarifaria'],
            data['consumo_m3'], data['dias_entre_lecturas'], data['lectura_estimada_flag'],
            data['clave_lectura_tipo'], data['antiguedad_medidor_meses'], data['mora_dias'],
            data['tiene_deuda_activa'], data['avg_consumo_6m'], data['std_consumo_6m'],
            data['var_pct_mes'], data['ceros_ult12'], data['temperatura_maxima'],
            data['precipitacion_acumulada'], data['sector_riesgo_0_1'], data['cluster_eps_id'],
            data['perfil_cluster_kmeans']
        ]])
        
        # Inferencia
        features_scaled = scaler.transform(features)
        prediccion = model.predict(features_scaled)[0]
        probabilidad = model.predict_proba(features_scaled)[0][1] # Probabilidad de Clase 1 (Fraude)
        
        if prediccion == 1:
            score = round(float(probabilidad) * 100, 2)
            print(f" [🚨 ALERTA] FRAUDE DETECTADO. Probabilidad: {score}%")
            
            alerta_df = pd.DataFrame([{
                'timestamp_alerta': datetime.now(),
                'codigo_cliente': data['codigo_cliente'],
                'cluster_eps_id': data['cluster_eps_id'],
                'consumo_m3_registrado': data['consumo_m3'],
                'score_irregular_pct': score,
                'estado_inspeccion': 'PENDIENTE_CAMPO'
            }])
            
            alerta_df.to_sql('alertas_irregularidades', engine, if_exists='append', index=False)
            print(" [💾] Alerta persistida en PostgreSQL.")
        else:
            print(" [✅] Lectura validada: Comportamiento Normal.")
            
        # Confirmar procesamiento exitoso
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except KeyError as e:
        print(f" [ERROR] Atributo faltante en JSON: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False) # No reencolar basura
    except Exception as e:
        print(f" [ERROR] Error en el pipeline: {e}")
        # Reencolar si es un error temporal (ej. caída de base de datos)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

# ==============================================================================
# INICIO DEL SERVICIO
# ==============================================================================
def iniciar_consumidor():
    # 1. Definir credenciales explícitas
    credentials = pika.PlainCredentials('admin', 'Admin123')
    
    # 2. Configurar parámetros con las credenciales
    params = pika.ConnectionParameters(
        host='127.0.0.1', 
        port=5672,
        credentials=credentials,
        heartbeat=600
    )
    
    try:
        # 3. Establecer conexión
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=procesar_medicion)
        
        print("\n" + "="*65)
        print(" 🤖 WORKER DE IA EN TIEMPO REAL OPERATIVO")
        print(f" 📡 Escuchando cola: '{QUEUE_NAME}'")
        print("="*65 + "\n")
        
        channel.start_consuming()
        
    except pika.exceptions.AMQPConnectionError:
        print(" [ERROR] No se pudo conectar a RabbitMQ. ¿Está el contenedor corriendo?")
    except KeyboardInterrupt:
        print(" [SISTEMA] Worker detenido por el usuario.")
        sys.exit(0)

if __name__ == '__main__':
    iniciar_consumidor()
