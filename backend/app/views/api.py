# backend/app/views/api.py
# backend/app/views/api.py
from flask import Blueprint, jsonify, current_app

api_bp = Blueprint("api", __name__)

@api_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "service": "backend"})

@api_bp.route("/ping-db", methods=["GET"])
def ping_db():
    try:
        db = current_app.extensions["db"]
        db.execute("SELECT 1;")
        one = db.fetchone()
        return jsonify({"db": "ok" if (one and one[0] == 1) else "fail"})
    except Exception as e:
        return jsonify({"db": "error", "detail": str(e)}), 500
