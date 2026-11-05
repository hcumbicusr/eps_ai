"""Tests de contrato Angular 22; sin levantar IA ni conectar a PostgreSQL."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.dashboard.router import router, get_dashboard_service


class DummyService:
    def summary(self):
        return {"origen": "postgresql:sidi_demo", "es_demo": True, "actualizado_en": "2026-11-05T00:00:00Z", "mediciones_total": 5984, "clientes_total": 1200, "alertas_total": 9, "lecturas_estimadas": 544, "consumo_promedio_m3": 24.1, "tasa_alertas_pct": .15}

    def detail(self):
        return {"origen": "postgresql:sidi_demo", "es_demo": True, "serie_mensual": [{"mes": "2025-01", "mediciones": 499, "alertas": 1}], "tipologias": [{"etiqueta": "Variación atípica", "cantidad": 4, "porcentaje": 44.44}], "sectores": [{"sector": "Sector A1", "mediciones": 1500, "alertas": 3, "riesgo_pct": .2}]}

    def alerts(self, sector, estado):
        assert sector in (None, "Sector A1")
        assert estado in (None, "PENDIENTE_CAMPO")
        return {"origen": "postgresql:sidi_demo", "es_demo": True, "total": 1, "items": [{"id": 1, "fecha": "2025-01-14", "cliente": "DEMO-00015", "sector": "Sector A1", "tipo": "Variación atípica", "score_pct": 92.4, "estado": "PENDIENTE_CAMPO"}]}


def client():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_dashboard_service] = DummyService
    return TestClient(app)


def test_resumen_contrato_angular():
    r = client().get("/api/dashboard/resumen")
    assert r.status_code == 200
    assert r.json()["mediciones_total"] == 5984
    assert r.json()["es_demo"] is True


def test_detalle_contrato_angular():
    r = client().get("/api/dashboard/detalle")
    assert r.status_code == 200
    assert r.json()["sectores"][0]["sector"] == "Sector A1"


def test_alertas_filtradas():
    r = client().get("/api/dashboard/alertas", params={"sector": "Sector A1", "estado": "PENDIENTE_CAMPO"})
    assert r.status_code == 200
    assert r.json()["items"][0]["id"] == 1


def test_filtro_no_acepta_texto_enorme():
    assert client().get("/api/dashboard/alertas", params={"sector": "x" * 81}).status_code == 422
