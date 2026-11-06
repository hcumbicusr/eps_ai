"""Persistencia transaccional e idempotente de eventos RabbitMQ.

Los datos recibidos se guardan incluso cuando no hay perfil para inferencia.
No escribe en sidi_demo ni en datasets de entrenamiento.
"""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.engine import Engine


def _uuid(value: str) -> str:
    return str(UUID(str(value)))


def save_received(engine: Engine, event: dict) -> str:
    event_id = _uuid(event['evento_id'])
    batch_id = _uuid(event['lote_id']) if event.get('lote_id') else None
    value = event.get('fecha_lectura')
    when = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    args = dict(
        evento_id=event_id, lote_id=batch_id, cliente=event['codigo_cliente'],
        fecha=when, consumo=float(event['consumo_m3']),
        estimada=bool(int(event.get('lectura_estimada_flag', 0))),
        origen='simulador' if event.get('origen') == 'simulador' else 'ingesta'
    )
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO sidi_live.mediciones
            (evento_id, lote_id, cliente_codigo, fecha_lectura, consumo_m3, lectura_estimada, origen)
            VALUES (:evento_id, :lote_id, :cliente, :fecha, :consumo, :estimada, :origen)
            ON CONFLICT (evento_id) DO NOTHING
        '''), args)
    return event_id


def already_finished(engine: Engine, event_id: str) -> bool:
    with engine.connect() as conn:
        status = conn.execute(text('SELECT estado_proceso FROM sidi_live.mediciones WHERE evento_id=:id'), {'id': event_id}).scalar_one()
    return status in ('EVALUADA', 'SIN_PERFIL', 'ERROR')


def finish(engine: Engine, event_id: str, *, status: str, sector: str = 'Sin perfil',
           prediction: int | None = None, score: float | None = None,
           error: str | None = None) -> None:
    if status not in ('EVALUADA', 'SIN_PERFIL', 'ERROR'):
        raise ValueError('Estado de procesamiento no permitido')
    with engine.begin() as conn:
        conn.execute(text('''
            UPDATE sidi_live.mediciones
            SET estado_proceso=:status, sector=:sector, codigo_prediccion=:prediction,
                score_irregular_pct=:score,
                estado_revision=CASE WHEN :prediction=1 THEN 'PENDIENTE_CAMPO' ELSE NULL END,
                detalle_error=:error, procesado_en=NOW()
            WHERE evento_id=:id AND estado_proceso='RECIBIDA'
        '''), dict(id=event_id, status=status, sector=sector,
                   prediction=prediction, score=score, error=(error or '')[:250] if error else None))
