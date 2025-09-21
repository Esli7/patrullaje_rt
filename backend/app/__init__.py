# backend/app/__init__.py
import os
from datetime import timedelta
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from app.config.settings import Settings
from app.core.db.factory import create_adapter

# Importa los blueprints
from app.endpoints.health import health_bp
from app.endpoints.auth import auth_bp
from app.endpoints.ubicaciones import ubic_bp
from app.views.web import web_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = Settings.SECRET_KEY

    # === CORS con credenciales ===
    FRONTEND_ORIGINS = "http://localhost:3000,http://localhost:8080"
    origins_csv = os.getenv("FRONTEND_ORIGINS", Settings.FRONTEND_ORIGIN)
    origins = [o.strip() for o in origins_csv.split(",") if o.strip()]

    CORS(
        app,
        resources={r"/*": {"origins": origins}},
        supports_credentials=True,
    )

    # === JWT cookies ===
    app.config["JWT_SECRET_KEY"] = Settings.JWT_SECRET
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_COOKIE_SECURE"] = Settings.COOKIE_SECURE
    app.config["JWT_COOKIE_SAMESITE"] = Settings.COOKIE_SAMESITE
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # lo puedes activar luego
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
        minutes=Settings.JWT_EXPIRES_MIN
    )
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

    # === Registrar blueprints ===
    app.register_blueprint(health_bp)     # /ping, /ping-db
    app.register_blueprint(web_bp)        # /
    app.register_blueprint(auth_bp)       # /auth/*
    app.register_blueprint(ubic_bp)       # /ubicaciones

    return app
