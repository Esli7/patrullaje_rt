# backend/app/endpoints/auth.py  (en tu repo está como app/core/endpoints/auth.py)
from datetime import timedelta
from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)
from app.services.user_service import UserService
from app.config.settings import Settings

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Instancia de servicio
user_service = UserService()


@auth_bp.record_once
def _ensure_schema(setup_state):
    # crear tablas (users, roles, user_roles) si no existen
    user_service.ensure_schema()


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    # nuevos (opcionales pero recomendados)
    nombre = (data.get("nombre") or None)
    nip = (data.get("nip") or None)

    if not email or not password:
        return jsonify({"ok": False, "msg": "email y password son requeridos"}), 400

    if user_service.get_by_email(email):
        return jsonify({"ok": False, "msg": "usuario ya existe"}), 409

    try:
        user = user_service.create_user(
            email=email,
            password=password,
            is_active=True,
            nombre=nombre,
            nip=nip,
        )
        # (Opcional) asigna rol operador por defecto
        try:
            user_service.assign_role(user["id"], "operador")
        except Exception:
            pass

        # devolvemos la versión pública (incluye nombre y nip desde el service)
        return jsonify({"ok": True, "user": user_service.public_user(user)}), 201

    except Exception as e:
        msg = str(e)
        # Manejo amable de unicidad (email o nip)
        if "users_email_key" in msg:
            return jsonify({"ok": False, "msg": "email ya registrado"}), 409
        if "ux_users_nip" in msg:
            return jsonify({"ok": False, "msg": "NIP ya registrado"}), 409
        return jsonify({"ok": False, "msg": f"error al registrar: {e}"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Modo híbrido:
      - Setea cookies httpOnly con access y refresh (frontend).
      - Devuelve access_token y refresh_token en JSON (clientes bearer).
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"ok": False, "msg": "email y password son requeridos"}), 400

    user = user_service.get_by_email(email)
    if not user or not user_service.verify_password(password, user["password_hash"]) or not user["is_active"]:
        return jsonify({"ok": False, "msg": "credenciales inválidas"}), 401

    expires = timedelta(minutes=int(Settings.JWT_EXPIRES_MIN))
    identity = str(user["id"])
    claims = {"email": user["email"]}  # puedes agregar 'nombre' si lo deseas

    access_token = create_access_token(
        identity=identity,
        additional_claims=claims,
        expires_delta=expires
    )
    refresh_token = create_refresh_token(
        identity=identity,
        additional_claims=claims,
    )

    # Respuesta para ambos mundos: JSON + cookies httpOnly
    resp = make_response(jsonify({
        "ok": True,
        "access_token": access_token,
        "refresh_token": refresh_token
    }))
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp, 200


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    Usa el refresh token (cookie o Authorization: Bearer) para emitir un nuevo access.
    - Siempre devuelve access_token en JSON.
    - Solo setea cookie de access si el refresh llegó por cookie (navegador).
    """
    identity = get_jwt_identity()
    claims = get_jwt()
    email = claims.get("email")

    user = user_service.get_by_email(email) if email else None
    if not identity or not user or not user.get("is_active", True):
        return jsonify({"ok": False, "msg": "no autorizado"}), 401

    expires = timedelta(minutes=int(Settings.JWT_EXPIRES_MIN))
    new_access = create_access_token(
        identity=str(identity),
        additional_claims={"email": email},
        expires_delta=expires,
    )

    # ¿El refresh vino por cookie? (navegador)
    came_from_cookie = "refresh_token_cookie" in request.cookies

    resp = make_response(jsonify({"ok": True, "access_token": new_access}))
    if came_from_cookie:
        # Para navegador, actualizamos cookie de access
        set_access_cookies(resp, new_access)
    return resp, 200


def _compute_primary_role(roles: list[str]) -> str:
    """
    Devuelve un rol efectivo estable priorizando admin > operador > patrullero > usuario.
    Si no hay roles, retorna 'usuario'.
    """
    roles = [str(r).strip().lower() for r in (roles or []) if str(r).strip()]
    priority = ["admin", "operador", "patrullero", "usuario"]
    for p in priority:
        if p in roles:
            return p
    return roles[0] if roles else "usuario"


@auth_bp.route("/me", methods=["GET"])
@jwt_required()  # acepta Authorization: Bearer ... o cookie httpOnly
def me():
    uid = get_jwt_identity()  # string
    claims = get_jwt()
    email = claims.get("email")

    if not uid or not email:
        return jsonify({"ok": False, "msg": "no autorizado"}), 401

    user = user_service.get_by_email(email)
    if not user:
        return jsonify({"ok": False, "msg": "no autorizado"}), 401

    roles = user_service.list_role_codes(user["id"]) or []
    is_admin = "admin" in roles
    role = _compute_primary_role(roles)

    # public_user(user) ya incluye nombre y nip
    return jsonify({
        "ok": True,
        "user": user_service.public_user(user),
        "roles": roles,
        "role": role,          # rol efectivo/primario
        "is_admin": is_admin
    }), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Cookies: borra access y refresh httpOnly.
    Bearer: stateless; para revocar usa blocklist de jti si lo necesitas.
    """
    resp = make_response(jsonify({"ok": True}))
    unset_jwt_cookies(resp)
    return resp, 200
