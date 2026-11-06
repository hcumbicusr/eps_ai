"""API de dashboard: fuentes demo cargada (demo) y flujo RabbitMQ/IA (flujo)."""
from functools import lru_cache
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from .models import AlertPage, DashboardDetail, DashboardSummary
from .service import DashboardService
from .live_service import LiveDashboardService

logger = logging.getLogger('sidi.dashboard')
router = APIRouter(prefix='/api/dashboard', tags=['Dashboards SIDI'])
Source = Literal['demo', 'flujo']


@lru_cache(maxsize=1)
def get_dashboard_service() -> DashboardService:
    from src.config import settings
    engine = create_engine(settings.get_db_uri(), pool_pre_ping=True, pool_size=3,
                           max_overflow=2, connect_args={'connect_timeout': 5})
    return DashboardService(engine)


def choose(fuente: Source, demo: DashboardService):
    return demo if fuente == 'demo' else LiveDashboardService(demo.engine)


def handle_query(fn):
    try:
        return fn()
    except SQLAlchemyError:
        logger.exception('Error consultando PostgreSQL sidi_demo/sidi_live')
        raise HTTPException(status_code=503, detail='Base de dashboards no disponible; revise las inicializaciones.')


@router.get('/resumen', response_model=DashboardSummary)
def resumen(
    fuente: Source = Query(default='demo', description='demo=datos semilla, flujo=eventos RabbitMQ/IA'),
    service: DashboardService = Depends(get_dashboard_service),
):
    return handle_query(choose(fuente, service).summary)


@router.get('/detalle', response_model=DashboardDetail)
def detalle(
    fuente: Source = Query(default='demo'),
    service: DashboardService = Depends(get_dashboard_service),
):
    return handle_query(choose(fuente, service).detail)


@router.get('/alertas', response_model=AlertPage)
def alertas(
    sector: str | None = Query(default=None, max_length=80),
    estado: str | None = Query(default=None, max_length=40),
    fuente: Source = Query(default='demo'),
    service: DashboardService = Depends(get_dashboard_service),
):
    return handle_query(lambda: choose(fuente, service).alerts(sector, estado))
