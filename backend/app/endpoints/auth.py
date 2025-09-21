# backend/app/endpoints/auth.py
from flask import Blueprint, request, jsonify, make_response
from datetime import timedelta
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
    get_jwt, set_access_cookies, unset_jwt_cookies
)
from app.services.user_service import UserService
from app.config.settings import Settings

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Instancia de servicio
user_service = UserService()

@auth_bp.record_once
def _ensure_schema(setup_state):
    # crear tabla users si no existe
    user_service.ensure_schema()

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"ok": False, "msg": "email y password son requeridos"}), 400

    if user_service.get_by_email(email):
        return jsonify({"ok": False, "msg": "usuario ya existe"}), 409

    try:
        user = user_service.create_user(email, password)
        return jsonify({"ok": True, "user": user_service.public_user(user)}), 201
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al registrar: {e}"}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"ok": False, "msg": "email y password son requeridos"}), 400

    user = user_service.get_by_email(email)
    if not user or not user_service.verify_password(password, user["password_hash"]) or not user["is_active"]:
        return jsonify({"ok": False, "msg": "credenciales inválidas"}), 401

    # JWT: identity debe ser string. info extra como claims.
    expires = timedelta(minutes=int(Settings.JWT_EXPIRES_MIN))
    access_token = create_access_token(
        identity=str(user["id"]),
        additional_claims={"email": user["email"]},
        expires_delta=expires
    )

    resp = make_response(jsonify({"ok": True}))
    set_access_cookies(resp, access_token)  # guarda JWT en cookie httpOnly
    return resp, 200

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    # identity llega como str (id del usuario)
    uid = get_jwt_identity()
    claims = get_jwt()  # aquí pusimos el email
    email = claims.get("email")

    if not uid or not email:
        return jsonify({"ok": False, "msg": "no autorizado"}), 401

    user = user_service.get_by_email(email)
    if not user:
        return jsonify({"ok": False, "msg": "no autorizado"}), 401

    return jsonify({"ok": True, "user": user_service.public_user(user)}), 200

@auth_bp.route("/logout", methods=["POST"])
def logout():
    resp = make_response(jsonify({"ok": True}))
    unset_jwt_cookies(resp)  # borra la cookie del JWT
    return resp, 200
