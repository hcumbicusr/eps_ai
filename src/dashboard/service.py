"""Consultas SQL de solo lectura sobre sidi_demo.

No accede a feature_store_lecturas, cliente_features, modelos o cola RabbitMQ.
Los indicadores provienen solo de tablas demo y NO son resultados reales de EPS.
"""
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Engine


class DashboardService:
    def __init__(self, engine: Engine):
        self.engine = engine

    def summary(self) -> dict:
        with self.engine.connect() as conn:
            m = conn.execute(text("""
                SELECT count(*)::int AS mediciones_total,
                       count(DISTINCT cliente_codigo)::int AS clientes_total,
                       count(*) FILTER (WHERE lectura_estimada)::int AS lecturas_estimadas,
                       coalesce(round(avg(consumo_m3), 2), 0)::float AS consumo_promedio_m3
                FROM sidi_demo.mediciones
            """)).mappings().one()
            alertas = conn.execute(text("SELECT count(*)::int FROM sidi_demo.alertas")).scalar_one()
        total = int(m["mediciones_total"])
        return {
            "origen": "postgresql:sidi_demo", "es_demo": True,
            "actualizado_en": datetime.now(timezone.utc).isoformat(),
            **dict(m), "alertas_total": int(alertas),
            "tasa_alertas_pct": round(100 * int(alertas) / total, 2) if total else 0.0,
        }

    def detail(self) -> dict:
        with self.engine.connect() as conn:
            months = conn.execute(text("""
                SELECT to_char(date_trunc('month', m.fecha_lectura), 'YYYY-MM') AS mes,
                       count(DISTINCT m.id)::int AS mediciones,
                       count(a.id)::int AS alertas
                FROM sidi_demo.mediciones m
                LEFT JOIN sidi_demo.alertas a ON a.medicion_id = m.id
                GROUP BY 1 ORDER BY 1
            """)).mappings().all()
            categories = conn.execute(text("""
                SELECT tipo AS etiqueta, count(*)::int AS cantidad
                FROM sidi_demo.alertas GROUP BY tipo ORDER BY cantidad DESC, etiqueta
            """)).mappings().all()
            sectors = conn.execute(text("""
                SELECT m.sector, count(m.id)::int AS mediciones,
                       count(a.id)::int AS alertas
                FROM sidi_demo.mediciones m
                LEFT JOIN sidi_demo.alertas a ON a.medicion_id = m.id
                GROUP BY m.sector ORDER BY alertas DESC, m.sector
            """)).mappings().all()
        total_alerts = sum(int(x["cantidad"]) for x in categories)
        return {
            "origen": "postgresql:sidi_demo", "es_demo": True,
            "serie_mensual": [dict(r) for r in months],
            "tipologias": [{**dict(r), "porcentaje": round(100 * int(r["cantidad"]) / total_alerts, 2) if total_alerts else 0} for r in categories],
            "sectores": [{**dict(r), "riesgo_pct": round(100 * int(r["alertas"]) / int(r["mediciones"]), 2) if r["mediciones"] else 0} for r in sectors],
        }

    def alerts(self, sector: str | None = None, estado: str | None = None) -> dict:
        """Filtrado con parámetros enlazados: nunca se concatena entrada de usuario a SQL."""
        clauses = []
        params: dict[str, str] = {}
        if sector and sector != "todos":
            clauses.append("m.sector = :sector")
            params["sector"] = sector
        if estado and estado != "todos":
            clauses.append("a.estado = :estado")
            params["estado"] = estado
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        tables = " FROM sidi_demo.alertas a JOIN sidi_demo.mediciones m ON m.id = a.medicion_id"
        with self.engine.connect() as conn:
            total = conn.execute(text("SELECT count(*)::int" + tables + where), params).scalar_one()
            rows = conn.execute(text("""
                SELECT a.id, to_char(a.fecha, 'YYYY-MM-DD') AS fecha,
                       m.cliente_codigo AS cliente, m.sector, a.tipo,
                       a.score_pct::float AS score_pct, a.estado
            """ + tables + where + " ORDER BY a.fecha DESC, a.id DESC LIMIT 100"), params).mappings().all()
        return {
            "origen": "postgresql:sidi_demo", "es_demo": True,
            "total": int(total), "items": [dict(r) for r in rows],
        }
