import os
import sys
import pika
import json
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from config import settings
from utils.logger_setup import setup_logger

# Se activa el log automáticamente
setup_logger("model_consumer")

print("\n" + "="*65)
print(" 🤖 INICIANDO MOTOR DE INFERENCIA IA (MODO ENRIQUECIMIENTO)")
print("="*65)

try:
    # Carga de artefactos usando rutas centralizadas
    scaler = joblib.load(settings.SCALER_PATH)
    model = joblib.load(settings.MODEL_PATH)
    
    # Motor de base de datos para Feature Store y persistencia de alertas
    engine = create_engine(settings.get_db_uri())
    
    print(" [✅] Modelos cargados en RAM.")
    print(f" [✅] Conexión establecida a Feature Store: {settings.DB_NAME}")
except Exception as e:
    print(f" [❌ ERROR CRÍTICO] Fallo en la inicialización: {e}")
    sys.exit(1)

# ==============================================================================
# LÓGICA DE ENRIQUECIMIENTO Y PREDICCIÓN
# ==============================================================================
def enriquecer_y_predecir(payload):
    codigo_cliente = payload.get('codigo_cliente')
    consumo_actual = float(payload.get('consumo_m3', 0))
    
    # 1. Consulta al Feature Store (Lookup indexado por PK)
    query = text("SELECT * FROM cliente_features WHERE codigo_cliente = :cliente")
    with engine.connect() as conn:
        perfil = conn.execute(query, {"cliente": codigo_cliente}).fetchone()
        
    if not perfil:
        print(f" [⚠️] Cliente {codigo_cliente} no hallado en Feature Store. Omitiendo.")
        return None

    # 2. Cálculo de métricas dinámicas (Cruce Tiempo Real + Histórico)
    avg_hist = float(perfil.avg_consumo_6m)
    var_pct_mes = ((consumo_actual - avg_hist) / avg_hist) if avg_hist > 0 else 0

    # 3. Ensamblaje del vector de 22 variables para el modelo
    # Se espera formato ISO de NestJS: "2026-03-10T12:00:00Z"
    try:
        fecha_str = payload.get('fecha_lectura', datetime.now().isoformat())
        fecha = datetime.fromisoformat(fecha_str.replace('Z', '+00:00'))
    except Exception:
        fecha = datetime.now()
    
    # IMPORTANTE: El orden de las columnas debe ser idéntico al entrenamiento
    X_inference = pd.DataFrame([{
        'mes_escalar': fecha.month,
        'contexto_estacional': int(fecha.month % 4), # Lógica estacional básica
        'es_fin_de_semana': 1 if fecha.weekday() >= 5 else 0,
        'es_mes_festivo': 0,
        'clase_servicio': perfil.clase_servicio,
        'categoria_tarifaria': perfil.categoria_tarifaria,
        'consumo_m3': consumo_actual,
        'dias_entre_lecturas': payload.get('dias_entre_lecturas', 30),
        'lectura_estimada_flag': payload.get('lectura_estimada_flag', 0),
        'clave_lectura_tipo': payload.get('clave_lectura_tipo', 1),
        'antiguedad_medidor_meses': perfil.antiguedad_medidor_meses,
        'mora_dias': perfil.mora_dias,
        'tiene_deuda_activa': perfil.tiene_deuda_activa,
        'avg_consumo_6m': avg_hist,
        'std_consumo_6m': float(perfil.std_consumo_6m),
        'var_pct_mes': var_pct_mes,
        'ceros_ult12': float(perfil.ceros_ult12),
        'temperatura_maxima': float(perfil.temperatura_maxima),
        'precipitacion_acumulada': float(perfil.precipitacion_acumulada),
        'sector_riesgo_0_1': float(perfil.sector_riesgo_0_1),
        'cluster_eps_id': perfil.cluster_eps_id,
        'perfil_cluster_kmeans': perfil.perfil_cluster_kmeans
    }])

    # 4. Inferencia con IA
    X_scaled = scaler.transform(X_inference)
    probabilidad = model.predict_proba(X_scaled)[0][1] # Probabilidad de Clase 1 (Fraude)
    prediccion = 1 if probabilidad > 0.5 else 0
    
    return {
        "score": round(float(probabilidad) * 100, 2),
        "prediccion": prediccion,
        "perfil": perfil
    }

def callback_procesamiento(ch, method, properties, body):
    try:
        mensaje_raw = json.loads(body)
        # NestJS suele enviar la data dentro de una propiedad 'data' o directo
        payload = mensaje_raw.get('data', mensaje_raw)
        
        print(f" [📥] Recibido Cliente: {payload.get('codigo_cliente')} | Consumo: {payload.get('consumo_m3')} m3")
        
        resultado = enriquecer_y_predecir(payload)
        
        if resultado and resultado['prediccion'] == 1:
            score = resultado['score']
            perfil = resultado['perfil']
            print(f" [🚨 ALERTA] FRAUDE DETECTADO ({score}%)")
            
            # Persistir alerta en PostgreSQL
            alerta_df = pd.DataFrame([{
                'timestamp_alerta': datetime.now(),
                'codigo_cliente': payload['codigo_cliente'],
                'cluster_eps_id': perfil.cluster_eps_id,
                'consumo_m3_registrado': payload['consumo_m3'],
                'score_irregular_pct': score,
                'estado_inspeccion': 'PENDIENTE_CAMPO'
            }])
            alerta_df.to_sql('alertas_irregularidades', engine, if_exists='append', index=False)
            print(" [💾] Registro guardado en alertas_irregularidades.")
        else:
            print(" [✅] Comportamiento Normal.")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f" [❌] Error en Pipeline: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

# ==============================================================================
# EJECUCIÓN DEL CONSUMIDOR
# ==============================================================================
def iniciar_consumidor():
    credentials = pika.PlainCredentials(settings.RABBIT_USER, settings.RABBIT_PASS)
    params = pika.ConnectionParameters(
        host=settings.RABBIT_HOST,
        port=settings.RABBIT_PORT,
        credentials=credentials,
        heartbeat=600
    )
    
    try:
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        
        # Declarar cola (Idempotente)
        channel.queue_declare(queue=settings.QUEUE_NAME_MEDICION_REGISTRADA, durable=True)
        channel.basic_qos(prefetch_count=1)
        
        print(f" 📡 Escuchando eventos en: {settings.QUEUE_NAME_MEDICION_REGISTRADA}...")
        channel.basic_consume(queue=settings.QUEUE_NAME_MEDICION_REGISTRADA, on_message_callback=callback_procesamiento)
        channel.start_consuming()
        
    except pika.exceptions.AMQPConnectionError:
        print(" [ERROR] Conexión a RabbitMQ fallida.")
    except KeyboardInterrupt:
        print(" [SISTEMA] Worker detenido.")
        sys.exit(0)

if __name__ == '__main__':
    iniciar_consumidor()