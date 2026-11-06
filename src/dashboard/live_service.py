"""Indicadores de eventos de la cola y del modelo, separados de sidi_demo.

La fuente contiene mediciones simuladas, por lo que es_demo permanece true.
No se infiere fraude confirmado: son alertas preliminares del clasificador.
"""
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.engine import Engine

SOURCE = 'postgresql:sidi_live'
ALERT_WHERE = "estado_proceso='EVALUADA' AND codigo_prediccion=1"


class LiveDashboardService:
    def __init__(self, engine: Engine):
        self.engine = engine

    def summary(self) -> dict:
        with self.engine.connect() as conn:
            r = conn.execute(text(f'''
                SELECT count(*)::int AS mediciones_total,
                       count(DISTINCT cliente_codigo)::int AS clientes_total,
                       count(*) FILTER (WHERE lectura_estimada)::int AS lecturas_estimadas,
                       COALESCE(round(avg(consumo_m3), 2),0)::float AS consumo_promedio_m3,
                       count(*) FILTER (WHERE {ALERT_WHERE})::int AS alertas_total,
                       count(*) FILTER (WHERE estado_proceso='EVALUADA')::int AS evaluadas_total,
                       count(*) FILTER (WHERE estado_proceso='SIN_PERFIL')::int AS sin_perfil_total,
                       count(*) FILTER (WHERE estado_proceso='ERROR')::int AS errores_total,
                       count(*) FILTER (WHERE estado_proceso='RECIBIDA')::int AS pendientes_total
                FROM sidi_live.mediciones
            ''')).mappings().one()
        result = dict(r)
        total = result['evaluadas_total']
        result.update(origen=SOURCE, es_demo=True, actualizado_en=datetime.now(timezone.utc).isoformat(),
                      tasa_alertas_pct=round(100 * result['alertas_total'] / total, 2) if total else 0)
        return result

    def detail(self) -> dict:
        with self.engine.connect() as conn:
            monthly = conn.execute(text(f'''
                SELECT to_char(date_trunc('month', fecha_recepcion AT TIME ZONE 'UTC'),'YYYY-MM') AS mes,
                    count(*)::int AS mediciones,
                    count(*) FILTER (WHERE {ALERT_WHERE})::int AS alertas
                FROM sidi_live.mediciones GROUP BY 1 ORDER BY 1
            ''')).mappings().all()
            sectors = conn.execute(text(f'''
                SELECT sector, count(*)::int AS mediciones,
                       count(*) FILTER (WHERE {ALERT_WHERE})::int AS alertas,
                       count(*) FILTER (WHERE estado_proceso='EVALUADA')::int AS evaluadas
                FROM sidi_live.mediciones GROUP BY sector ORDER BY alertas DESC, sector
            ''')).mappings().all()
            alerts = conn.execute(text(f'''
                SELECT count(*)::int FROM sidi_live.mediciones WHERE {ALERT_WHERE}
            ''')).scalar_one()
        return {
            'origen': SOURCE, 'es_demo': True,
            'serie_mensual': [dict(x) for x in monthly],
            'tipologias': ([{'etiqueta': 'Alerta de irregularidad (IA)', 'cantidad': alerts, 'porcentaje': 100.0}]
                           if alerts else []),
            'sectores': [dict(sector=x['sector'], mediciones=x['mediciones'], alertas=x['alertas'],
                              riesgo_pct=round(100*x['alertas']/x['evaluadas'],2) if x['evaluadas'] else 0.0)
                         for x in sectors],
        }

    def alerts(self, sector: str | None = None, estado: str | None = None) -> dict:
        clauses = [ALERT_WHERE]
        params = {}
        if sector and sector != 'todos':
            clauses.append('sector=:sector')
            params['sector'] = sector
        if estado and estado != 'todos':
            clauses.append('estado_revision=:estado')
            params['estado'] = estado
        where = ' AND '.join(clauses)
        with self.engine.connect() as conn:
            total = conn.execute(text(f'SELECT count(*)::int FROM sidi_live.mediciones WHERE {where}'), params).scalar_one()
            rows = conn.execute(text(f'''
                SELECT evento_id::text AS id,
                       to_char(fecha_recepcion AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS') AS fecha,
                       cliente_codigo AS cliente, sector,
                       'Alerta de irregularidad (IA)' AS tipo,
                       score_irregular_pct::float AS score_pct,
                       estado_revision AS estado
                FROM sidi_live.mediciones
                WHERE {where} ORDER BY fecha_recepcion DESC, evento_id DESC LIMIT 100
            '''), params).mappings().all()
        return {'origen': SOURCE, 'es_demo': True, 'total': total, 'items': [dict(x) for x in rows]}
