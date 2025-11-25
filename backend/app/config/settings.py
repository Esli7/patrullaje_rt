# backend/app/config/settings.py
import os
from urllib.parse import quote_plus


class Settings:
    # === SECRET / COOKIES ===
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # === DB ===
    DB_ENGINE = os.getenv("DB_ENGINE", "postgres")
    DB_HOST = os.getenv("DB_HOST", "patrol_db")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "patrullaje_db")
    DB_USER = os.getenv("DB_USER", "patrol_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "supersegura")

    # Parámetros opcionales de pool (seguros por defecto)
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # segundos

    # === JWT / CORS ===
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-change-me")

    # Acepta uno o varios orígenes separados por coma; soporta ambas vars
    FRONTEND_ORIGIN = os.getenv(
        "FRONTEND_ORIGIN",
        os.getenv("FRONTEND_ORIGINS", "http://localhost:3000"),
    )

    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")
    JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "480"))


def split_origins(value: str) -> list[str]:
    """Convierte 'a,b,c' en ['a','b','c'] eliminando espacios/vacíos."""
    return [o.strip() for o in (value or "").split(",") if o and o.strip()]


def build_sqlalchemy_uri(cfg: "Settings") -> str:
    """
    Construye la URI para SQLAlchemy usando psycopg v3.
    Formato: postgresql+psycopg://user:pass@host:port/db
    """
    engine = (cfg.DB_ENGINE or "postgres").lower()
    if engine in ("postgres", "postgresql", "postgis"):
        user = quote_plus(cfg.DB_USER)
        pwd = quote_plus(cfg.DB_PASSWORD)
        return f"postgresql+psycopg://{user}:{pwd}@{cfg.DB_HOST}:{cfg.DB_PORT}/{cfg.DB_NAME}"
    raise ValueError(f"DB_ENGINE no soportado: {engine}")


def sqlalchemy_engine_kwargs(cfg: "Settings") -> dict:
    """Parámetros de pool para create_engine (opcionales)."""
    return {
        "pool_size": cfg.DB_POOL_SIZE,
        "max_overflow": cfg.DB_MAX_OVERFLOW,
        "pool_pre_ping": cfg.DB_POOL_PRE_PING,
        "pool_recycle": cfg.DB_POOL_RECYCLE,
    }
