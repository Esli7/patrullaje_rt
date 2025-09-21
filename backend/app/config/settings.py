# backend/app/config/settings.py
import os

class Settings:
    # ... (tus DB_*, SECRET_KEY ya existen)
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    DB_ENGINE = os.getenv("DB_ENGINE", "postgres")
    DB_HOST = os.getenv("DB_HOST", "patrol_db")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "patrullaje_db")
    DB_USER = os.getenv("DB_USER", "patrol_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "supersegura")

    # NEW: JWT / CORS
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-change-me")
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")
    JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "480"))
