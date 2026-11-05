"""Carga el esquema sidi_demo mediante credenciales POSTGRES_* o DB_*.

Uso desde raíz: python scripts/dashboard/seed_demo.py
No instala extensiones y no modifica tablas de entrenamiento ni inferencia.
"""
import os
from pathlib import Path
import psycopg2


def main() -> None:
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    user = os.getenv("DB_USER", os.getenv("POSTGRES_USER", "postgres"))
    password = os.getenv("DB_PASS", os.getenv("POSTGRES_PASSWORD", ""))
    database = os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "eps_db"))
    script = Path(__file__).with_name("seed_sidi_demo.sql").read_text(encoding="utf-8")
    with psycopg2.connect(host=host, port=port, user=user, password=password, dbname=database, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(script)
            cur.execute("SELECT (SELECT count(*) FROM sidi_demo.mediciones), (SELECT count(*) FROM sidi_demo.alertas)")
            measurements, alerts = cur.fetchone()
    print(f"Semilla sidi_demo verificada: mediciones={measurements}, alertas={alerts}")


if __name__ == "__main__":
    main()
