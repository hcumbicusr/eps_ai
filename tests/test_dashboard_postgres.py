"""Prueba con PostgreSQL real, habilitada con SIDI_TEST_DB_URL en CI."""
import os
import pytest
from sqlalchemy import create_engine, text
from src.dashboard.service import DashboardService


@pytest.mark.skipif(not os.getenv("SIDI_TEST_DB_URL"), reason="Sin BD aislada de integración")
def test_postgresql_seed_and_filters():
    engine = create_engine(os.environ["SIDI_TEST_DB_URL"], pool_pre_ping=True)
    service = DashboardService(engine)
    s = service.summary()
    assert s["mediciones_total"] == 5984
    assert s["clientes_total"] == 1200
    assert s["alertas_total"] == 9
    assert s["es_demo"] is True
    d = service.detail()
    assert sum(row["mediciones"] for row in d["serie_mensual"]) == 5984
    assert sum(row["alertas"] for row in d["serie_mensual"]) == 9
    assert sum(row["cantidad"] for row in d["tipologias"]) == 9
    assert sum(row["mediciones"] for row in d["sectores"]) == 5984
    assert sum(row["alertas"] for row in d["sectores"]) == 9
    assert service.alerts()["total"] == 9
    filtered = service.alerts(estado="PENDIENTE_CAMPO")
    assert filtered["total"] == 4
    assert all(x["estado"] == "PENDIENTE_CAMPO" for x in filtered["items"])
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM sidi_demo.alertas")).scalar_one() == 9
