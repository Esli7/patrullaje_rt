# backend/app/__init__.py
from datetime import timedelta

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from sqlalchemy import create_engine

from app.endpoints.patrullas import patrullas_bp
from app.endpoints.asignaciones import asig_bp  # <-- NUEVO

from app.config.settings import (
    Settings,
    build_sqlalchemy_uri,
    split_origins,
    sqlalchemy_engine_kwargs,
)

from app.views.api import api_bp       # /api/ping, /api/ping-db
from app.views.web import web_bp       # /
from app.endpoints.ubicaciones import ubic_bp
from app.endpoints.auth import auth_bp              # /api/auth/*
from app.endpoints.users import users_bp            # /api/users/*
from app.endpoints.mobile import mobile_bp   # ← NUEVO


def create_app() -> Flask:
    app = Flask(__name__)

    # === Secret & JWT ===
    app.config["SECRET_KEY"] = Settings.SECRET_KEY
    app.config["JWT_SECRET_KEY"] = Settings.JWT_SECRET
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=Settings.JWT_EXPIRES_MIN)

    # --- JWT: modo híbrido (cookies + headers Bearer) ---
    app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"

    # Cookies httpOnly para los tokens (en dev: secure=False / SameSite=Lax)
    app.config["JWT_COOKIE_SECURE"] = Settings.COOKIE_SECURE        # False en dev
    app.config["JWT_COOKIE_SAMESITE"] = Settings.COOKIE_SAMESITE    # "Lax" en dev
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # en prod puedes activarlo

    # === CORS SOLO para /api/* ===
    cfg_origins = split_origins(Settings.FRONTEND_ORIGIN) or []
    dev_origins = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    origins = sorted(set(cfg_origins + dev_origins)) or ["http://localhost:5500"]

    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/api/*": {
                "origins": origins,
                "allow_headers": ["Content-Type", "Authorization"],
                "expose_headers": ["Content-Type"],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "vary_header": True,
                "max_age": 86400,
            }
        },
    )

    # === DB Engine compartido ===
    db_uri = build_sqlalchemy_uri(Settings)
    engine = create_engine(db_uri, **sqlalchemy_engine_kwargs(Settings))
    app.extensions["db_engine"] = engine

    # === JWT ===
    JWTManager(app)

    # === Blueprints (todas las rutas de API quedan bajo /api/...) ===
    app.register_blueprint(api_bp,          url_prefix="/api")               # /api/ping, /api/ping-db
    app.register_blueprint(ubic_bp,         url_prefix="/api/ubicaciones")   # /api/ubicaciones/*
    app.register_blueprint(auth_bp,         url_prefix="/api/auth")          # /api/auth/*
    app.register_blueprint(users_bp,        url_prefix="/api/users")         # /api/users/*
    app.register_blueprint(patrullas_bp,    url_prefix="/api/patrullas")     # /api/patrullas/*
    app.register_blueprint(asig_bp,         url_prefix="/api/asignaciones") 
    app.register_blueprint(mobile_bp, url_prefix="/api/mobile")  # ← NUEVO
    app.register_blueprint(web_bp)                                           # /

    return app
