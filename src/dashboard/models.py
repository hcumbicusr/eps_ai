"""Contratos HTTP consumidos por hcumbicusr/eps-front (Angular 22)."""
from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    origen: str
    es_demo: bool = True
    actualizado_en: str
    mediciones_total: int = Field(ge=0)
    clientes_total: int = Field(ge=0)
    alertas_total: int = Field(ge=0)
    lecturas_estimadas: int = Field(ge=0)
    consumo_promedio_m3: float = Field(ge=0)
    tasa_alertas_pct: float = Field(ge=0)
    evaluadas_total: int = Field(default=0, ge=0)
    sin_perfil_total: int = Field(default=0, ge=0)
    errores_total: int = Field(default=0, ge=0)
    pendientes_total: int = Field(default=0, ge=0)


class MonthlyPoint(BaseModel):
    mes: str
    mediciones: int
    alertas: int


class BreakdownItem(BaseModel):
    etiqueta: str
    cantidad: int
    porcentaje: float | None = None


class SectorItem(BaseModel):
    sector: str
    mediciones: int
    alertas: int
    riesgo_pct: float


class DashboardDetail(BaseModel):
    origen: str
    es_demo: bool = True
    serie_mensual: list[MonthlyPoint]
    tipologias: list[BreakdownItem]
    sectores: list[SectorItem]


class AlertItem(BaseModel):
    id: int | str
    fecha: str
    cliente: str
    sector: str
    tipo: str
    score_pct: float
    estado: str


class AlertPage(BaseModel):
    origen: str
    es_demo: bool = True
    total: int
    items: list[AlertItem]
