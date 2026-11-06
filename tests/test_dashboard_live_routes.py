"""El endpoint sigue disponible con fuente=demo y rechaza fuentes inexistentes."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.dashboard.router import get_dashboard_service, router


class Dummy:
    def summary(self):
        return {'origen':'postgresql:sidi_demo','es_demo':True,'actualizado_en':'2026-11-06T10:00:00Z',
                'mediciones_total':1,'clientes_total':1,'alertas_total':0,'lecturas_estimadas':0,
                'consumo_promedio_m3':20.0,'tasa_alertas_pct':0.0}


def test_demo_unchanged_and_unknown_source_rejected():
    app=FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_dashboard_service]=lambda:Dummy()
    client=TestClient(app)
    assert client.get('/api/dashboard/resumen').status_code == 200
    assert client.get('/api/dashboard/resumen?fuente=demo').json()['mediciones_total'] == 1
    assert client.get('/api/dashboard/resumen?fuente=intruso').status_code == 422
