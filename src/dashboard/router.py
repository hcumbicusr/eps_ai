"""Submódulo FastAPI de consultas; no modifica la inferencia /predict."""
from functools import lru_cache
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from .models import AlertPage, DashboardDetail, DashboardSummary
from .service import DashboardService

logger = logging.getLogger("sidi.dashboard")
router = APIRouter(prefix="/api/dashboard", tags=["Dashboards demo"])


@lru_cache(maxsize=1)
def get_dashboard_service() -> DashboardService:
    from src.config import settings  # importación diferida, permite pruebas aisladas
    engine = create_engine(settings.get_db_uri(), pool_pre_ping=True, pool_size=3, max_overflow=2, connect_args={"connect_timeout": 5})
    return DashboardService(engine)


def handle_query(fn):
    try:
        return fn()
    except SQLAlchemyError:
        logger.exception("Fallo de consulta sidi_demo; compruebe la carga inicial de la BD")
        raise HTTPException(status_code=503, detail="Base de demostración no disponible; ejecute la carga sidi_demo.")


@router.get("/resumen", response_model=DashboardSummary)
def resumen(service: DashboardService = Depends(get_dashboard_service)):
    return handle_query(service.summary)


@router.get("/detalle", response_model=DashboardDetail)
def detalle(service: DashboardService = Depends(get_dashboard_service)):
    return handle_query(service.detail)


@router.get("/alertas", response_model=AlertPage)
def alertas(
    sector: str | None = Query(default=None, max_length=80),
    estado: str | None = Query(default=None, max_length=40),
    service: DashboardService = Depends(get_dashboard_service),
):
    return handle_query(lambda: service.alerts(sector, estado))
