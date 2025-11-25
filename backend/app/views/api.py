# backend/app/views/api.py
from flask import Blueprint, jsonify, current_app
from sqlalchemy import text  # <-- NECESARIO en SQLAlchemy 2.x

api_bp = Blueprint("api", __name__)

@api_bp.get("/ping")
def ping():
    return jsonify({"status": "ok", "service": "backend"})

@api_bp.get("/ping-db")
def ping_db():
    try:
        engine = current_app.extensions.get("db_engine")
        if engine is None:
            return jsonify({"db": "not-initialized"}), 500
        with engine.connect() as conn:
            # En SQLAlchemy 2.x hay que envolver el SQL literal con text()
            one = conn.execute(text("SELECT 1")).scalar()
        return jsonify({"db": "ok" if one == 1 else "fail"})
    except Exception as e:
        return jsonify({"db": "error", "detail": str(e)}), 500
