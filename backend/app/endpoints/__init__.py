
from app.endpoints.ubicaciones import ubic_bp
from flask import Flask
from app.config.settings import Settings
from app.core.db.factory import create_adapter

# Endpoints (HTTP/API)
from app.endpoints.health import health_bp
from app.endpoints.ubicaciones import ubic_bp

# Vistas HTML (si usas Jinja/páginas)
from app.views.web import web_bp
def create_app():
    app = Flask(__name__)
    app.secret_key = Settings.SECRET_KEY

    db = create_adapter(
        Settings.DB_ENGINE,
        host=Settings.DB_HOST, port=Settings.DB_PORT,
        name=Settings.DB_NAME, user=Settings.DB_USER, password=Settings.DB_PASSWORD
    )
    db.connect()
    app.extensions["db"] = db

    # Capa de endpoints (API)
    app.register_blueprint(health_bp)    # /ping, /ping-db
    app.register_blueprint(ubic_bp)      # /api/v1/*
    app.register_blueprint(ubic_bp) 

    # Vistas web (HTML)
    app.register_blueprint(web_bp)       # /

    return app
