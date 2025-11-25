# backend/app/core/__init__.py
import os
from datetime import timedelta
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from app.config.settings import Settings
from app.core.db.factory import create_adapter
from app.views.api import api_bp
from app.views.web import web_bp

# 👇 NUEVO: importa el blueprint de patrullas
from app.endpoints.patrullas import patrullas_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = Settings.SECRET_KEY

    # === CORS ===
    FRONTEND_ORIGINS = "http://localhost:3000,http://localhost:8080,http://localhost:5500,http://127.0.0.1:5500"
    origins_csv = os.getenv("FRONTEND_ORIGINS", FRONTEND_ORIGINS)
    origins = [o.strip() for o in origins_csv.split(",") if o.strip()]

    CORS(
        app,
        resources={r"/api/*": {"origins": origins}},
        supports_credentials=True,  # necesario para cookies
    )

    # === JWT en cookies ===
    app.config["JWT_SECRET_KEY"] = Settings.JWT_SECRET
    app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]  # híbrido
    app.config["JWT_HEADER_NAME"] = "Authorization"
    app.config["JWT_HEADER_TYPE"] = "Bearer"
    app.config["JWT_COOKIE_SECURE"] = Settings.COOKIE_SECURE  # False en dev
    app.config["JWT_COOKIE_SAMESITE"] = Settings.COOKIE_SAMESITE  # "Lax" en dev
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=Settings.JWT_EXPIRES_MIN)
    JWTManager(app)

    # === DB adapter ===
    db = create_adapter(
        Settings.DB_ENGINE,
        host=Settings.DB_HOST,
        port=Settings.DB_PORT,
        name=Settings.DB_NAME,
        user=Settings.DB_USER,
        password=Settings.DB_PASSWORD,
    )
    try:
        db.connect()
        app.extensions["db"] = db
    except Exception as e:
        app.extensions["db"] = db
        app.extensions["db_error"] = str(e)

    # === Blueprints ===
    app.register_blueprint(api_bp, url_prefix="/api")  # /api/ping, /api/ping-db
    # 👇 NUEVO: expone /api/patrullas/*
    app.register_blueprint(patrullas_bp, url_prefix="/api/patrullas")
    app.register_blueprint(web_bp)  # vistas web

    return app
