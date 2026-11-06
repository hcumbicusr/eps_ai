"""Pruebas de la integración real de PostgreSQL para sidi_live.

Se ejecutan únicamente sobre el PostgreSQL efímero de GitHub Actions.
"""
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from src.dashboard.live_store import save_received, already_finished, finish
from src.dashboard.live_service import LiveDashboardService


@pytest.mark.skipif(not os.getenv('SIDI_TEST_DB_URL'), reason='Sin BD de integración')
def test_live_store_and_live_aggregates():
    engine = create_engine(os.environ['SIDI_TEST_DB_URL'], pool_pre_ping=True)
    service = LiveDashboardService(engine)
    events = [str(uuid4()) for _ in range(4)]
    fixture = dict(fecha_lectura='2026-11-06T12:00:00Z', consumo_m3=25,
                   lectura_estimada_flag=0, origen='simulador')
    for i, event in enumerate(events):
        save_received(engine, {**fixture, 'evento_id':event,'codigo_cliente':f'C{i:05d}'})
    save_received(engine, {**fixture, 'evento_id':events[0],'codigo_cliente':'C00000'})
    assert not already_finished(engine, events[0])
    finish(engine,events[0],status='EVALUADA',sector='Sector A1',prediction=1,score=91.0)
    finish(engine,events[1],status='EVALUADA',sector='Sector A1',prediction=0,score=11.0)
    finish(engine,events[2],status='SIN_PERFIL')
    finish(engine,events[3],status='ERROR',error='Error controlado en prueba')
    assert already_finished(engine, events[0])
    summary = service.summary()
    assert summary['mediciones_total'] == 4
    assert summary['evaluadas_total'] == 2
    assert summary['sin_perfil_total'] == 1
    assert summary['errores_total'] == 1
    assert summary['alertas_total'] == 1
    assert summary['tasa_alertas_pct'] == 50.0
    details = service.detail()
    assert sum(p['mediciones'] for p in details['serie_mensual']) == 4
    assert sum(p['alertas'] for p in details['serie_mensual']) == 1
    assert service.alerts()['total'] == 1
    assert service.alerts(sector='Sector A1',estado='PENDIENTE_CAMPO')['total']==1
    assert service.alerts(sector='Sector A2')['total'] == 0
    with engine.connect() as conn:
        count=conn.execute(text('SELECT count(*) FROM sidi_live.mediciones')).scalar_one()
    assert count == 4
