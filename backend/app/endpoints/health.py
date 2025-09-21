from flask import Blueprint, jsonify, current_app as app

health_bp = Blueprint("health", __name__)

@health_bp.get("/ping")
def ping():
    return jsonify({"ok": True, "msg": "pong"})

@health_bp.get("/ping-db")
def ping_db():
    db = app.extensions["db"]
    db.execute("SELECT NOW()")
    now = db.fetchone()[0]
    return jsonify({"ok": True, "db_time": str(now)})
