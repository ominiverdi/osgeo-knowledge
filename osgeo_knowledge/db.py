"""Database connection and query helpers for osgeo-knowledge."""

import os
import logging
from pathlib import Path
from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

logger = logging.getLogger("osgeo_knowledge.db")

# Load .env from project root
_project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=_project_root / ".env")


def get_connection():
    """Get a PostgreSQL database connection.

    Connection parameters come from environment variables:
        DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

    If DB_HOST is empty, connects via Unix socket (peer auth).
    """
    params = {
        "database": os.getenv("DB_NAME", "osgeo_wiki"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
        "port": os.getenv("DB_PORT", "5432"),
    }

    host = os.getenv("DB_HOST", "")
    if host:
        params["host"] = host

    return psycopg2.connect(**params)


def fetch_all(sql: str, params: tuple = (), limit: int = 50) -> list[dict[str, Any]]:
    """Execute a query and return all results as list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows[:limit]]
    except Exception as e:
        logger.error("Query error: %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_one(sql: str, params: tuple = ()) -> Optional[dict[str, Any]]:
    """Execute a query and return a single result as dict, or None."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        logger.error("Query error: %s", e)
        conn.rollback()
        raise
    finally:
        conn.close()
