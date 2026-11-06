"""Consumidor SIDI: persiste todas las mediciones e inferencias para el dashboard.

Mantiene los 22 predictores y los artefactos de inferencia heredados. Una alerta
es una predicción preliminar y NO acredita fraude real.
"""
import json
import sys
import time
from datetime import datetime, timezone
from uuid import uuid4

import joblib
import pandas as pd
import pika
from sqlalchemy import create_engine, text

from config import settings
from utils.logger_setup import setup_logger
from src.dashboard.live_store import save_received, already_finished, finish

setup_logger('model_consumer')

try:
    scaler = joblib.load(settings.SCALER_PATH)
    model = joblib.load(settings.MODEL_PATH)
    engine = create_engine(settings.get_db_uri(), pool_pre_ping=True)
    print('[SIDI] Consumer inicializado con modelo y escalador de despliegue.')
except Exception as exc:
    print(f'[SIDI] Error crítico al inicializar el consumidor: {exc}')
    sys.exit(1)


def evaluate(payload: dict):
    cliente = payload['codigo_cliente']
    consumo_actual = float(payload['consumo_m3'])
    with engine.connect() as conn:
        perfil = conn.execute(text('SELECT * FROM cliente_features WHERE codigo_cliente=:codigo'),
                              {'codigo': cliente}).mappings().first()
    if perfil is None:
        return None

    valor_fecha = payload.get('fecha_lectura') or datetime.now(timezone.utc).isoformat()
    fecha = datetime.fromisoformat(str(valor_fecha).replace('Z', '+00:00'))
    avg_hist = float(perfil['avg_consumo_6m'] or 0.0)
    var_pct_mes = ((consumo_actual - avg_hist) / avg_hist) if avg_hist > 0 else 0.0
    features = pd.DataFrame([{
        'mes_escalar': fecha.month,
        'contexto_estacional': fecha.month % 4,
        'es_fin_de_semana': int(fecha.weekday() >= 5),
        'es_mes_festivo': int(fecha.month in (7, 12)),
        'clase_servicio': perfil['clase_servicio'],
        'categoria_tarifaria': perfil['categoria_tarifaria'],
        'consumo_m3': consumo_actual,
        'dias_entre_lecturas': int(payload.get('dias_entre_lecturas', 30)),
        'lectura_estimada_flag': int(payload.get('lectura_estimada_flag', 0)),
        'clave_lectura_tipo': int(payload.get('clave_lectura_tipo', 1)),
        'antiguedad_medidor_meses': perfil['antiguedad_medidor_meses'],
        'mora_dias': perfil['mora_dias'],
        'tiene_deuda_activa': perfil['tiene_deuda_activa'],
        'avg_consumo_6m': avg_hist,
        'std_consumo_6m': float(perfil['std_consumo_6m']),
        'var_pct_mes': var_pct_mes,
        'ceros_ult12': float(perfil['ceros_ult12']),
        'temperatura_maxima': float(perfil['temperatura_maxima']),
        'precipitacion_acumulada': float(perfil['precipitacion_acumulada']),
        'sector_riesgo_0_1': float(perfil['sector_riesgo_0_1']),
        'cluster_eps_id': int(perfil['cluster_eps_id']),
        'perfil_cluster_kmeans': int(perfil['perfil_cluster_kmeans']),
    }])
    scores = model.predict_proba(scaler.transform(features))[0]
    score = round(float(scores[1]) * 100, 2)
    prediction = int(score > 50.0)
    return {'sector': f"Sector A{perfil['cluster_eps_id']}",
            'prediction': prediction, 'score': score}


def callback_procesamiento(channel, method, properties, body):
    event_id = None
    try:
        message = json.loads(body)
        payload = message.get('data', message)
        payload.setdefault('evento_id', str(uuid4()))  # compatibilidad con mensajes antiguos
        event_id = save_received(engine, payload)
        if already_finished(engine, event_id):
            print(f'[SIDI] Evento duplicado resuelto: {event_id}')
            channel.basic_ack(delivery_tag=method.delivery_tag)
            return

        result = evaluate(payload)
        if result is None:
            finish(engine, event_id, status='SIN_PERFIL')
            print(f"[SIDI] Sin perfil: {payload.get('codigo_cliente')} | evento={event_id}")
        else:
            finish(engine, event_id, status='EVALUADA', sector=result['sector'],
                   prediction=result['prediction'], score=result['score'])
            print(f"[SIDI] Evaluada: {payload['codigo_cliente']} | clase={result['prediction']} "
                  f"| score={result['score']}% | evento={event_id}")
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        print(f'[SIDI] Fallo del mensaje: {exc}')
        if event_id:
            try:
                finish(engine, event_id, status='ERROR', error=str(exc))
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return
            except Exception as persist_exc:
                print(f'[SIDI] No se pudo registrar el error en PostgreSQL: {persist_exc}')
        # Reintento espaciado para impedir un bucle intensivo de reencolado.
        time.sleep(2)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def iniciar_consumidor():
    creds = pika.PlainCredentials(settings.RABBIT_USER, settings.RABBIT_PASS)
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=settings.RABBIT_HOST, port=settings.RABBIT_PORT,
        credentials=creds, heartbeat=600))
    try:
        ch = connection.channel()
        ch.queue_declare(queue=settings.QUEUE_NAME_MEDICION_REGISTRADA, durable=True)
        ch.basic_qos(prefetch_count=1)
        ch.basic_consume(queue=settings.QUEUE_NAME_MEDICION_REGISTRADA,
                         on_message_callback=callback_procesamiento)
        print(f'[SIDI] Esperando eventos en {settings.QUEUE_NAME_MEDICION_REGISTRADA}')
        ch.start_consuming()
    finally:
        if connection.is_open:
            connection.close()


if __name__ == '__main__':
    iniciar_consumidor()
