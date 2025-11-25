# backend/app/endpoints/users.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.user_service import UserService

users_bp = Blueprint("users", __name__, url_prefix="/users")
_user_svc = UserService()

# --- Conjunto de roles permitidos en la app ---
ALLOWED_ROLE_CODES = {"admin", "patrullero", "usuario"}

# Regex NIP: exactamente 5 dígitos, guion y 1 letra mayúscula (p.ej. 52134-P)
NIP_RE = re.compile(r"^[0-9]{5}-[A-Z]$")


@users_bp.record_once
def _ensure_schema(_state):
    """
    Garantiza que existan las tablas necesarias al registrar el blueprint.
    Intenta también 'sembrar' los roles básicos si el servicio lo soporta.
    No tumba si ya existen o el servicio no tiene esos métodos.
    """
    try:
        _user_svc.ensure_schema()
    except Exception as e:
        print(f"[users] ensure_schema warning: {e}")

    # Seed de roles conocidos (best-effort)
    try:
        # Preferimos un método "bulk" si existe
        if hasattr(_user_svc, "ensure_roles_exist"):
            _user_svc.ensure_roles_exist(list(ALLOWED_ROLE_CODES))
            return

        for code in ALLOWED_ROLE_CODES:
            try:
                if hasattr(_user_svc, "ensure_role"):
                    _user_svc.ensure_role(code)
                elif hasattr(_user_svc, "create_role_if_not_exists"):
                    _user_svc.create_role_if_not_exists(code)
                elif hasattr(_user_svc, "create_role"):
                    try:
                        _user_svc.create_role(code)
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception as e:
        print(f"[users] seed roles warning: {e}")


# --------- Helpers ---------
def _current_uid_int() -> Optional[int]:
    uid_str = get_jwt_identity()
    try:
        return int(uid_str) if uid_str is not None else None
    except (TypeError, ValueError):
        return None


def _is_admin(uid: Optional[int]) -> bool:
    if not uid:
        return False
    try:
        roles = _user_svc.list_role_codes(uid)  # e.g. ["admin", "operador"]
        return "admin" in (roles or [])
    except Exception:
        # Si el servicio aún no soporta roles, por seguridad asumimos NO admin
        return False


def _admin_guard() -> Optional[Tuple[dict, int]]:
    """
    Retorna una respuesta (json, status) si NO es admin. Si es admin -> None.
    Debe llamarse dentro de handler con @jwt_required()
    """
    uid = _current_uid_int()
    if uid is None:
        return {"ok": False, "msg": "no autorizado"}, 401
    if not _is_admin(uid):
        return {"ok": False, "msg": "permiso denegado"}, 403
    return None


def _normalize_roles_payload(payload_roles) -> Tuple[List[str], List[str]]:
    """
    Normaliza una lista de roles del payload a minúsculas y valida.
    Retorna (roles_validos, roles_invalidos)
    """
    if not isinstance(payload_roles, list):
        return [], []
    roles = [str(r).strip().lower() for r in payload_roles if str(r).strip()]
    invalid = [r for r in roles if r not in ALLOWED_ROLE_CODES]
    valid = [r for r in roles if r in ALLOWED_ROLE_CODES]
    return valid, invalid


def _inject_roles(u: Dict[str, Any]) -> Dict[str, Any]:
    """
    Asegura que el dict usuario incluya:
      - roles: List[str]
      - role: str | None (primer rol, compat)
      - role_display: str | None (roles unidos por coma)
    Si el servicio ya trae roles, se respetan; si no, se consultan.
    """
    if not isinstance(u, dict):
        return u

    user_id = u.get("id") or u.get("user_id") or u.get("_id")
    roles = u.get("roles")

    # Si ya trae lista, la normalizamos suave
    if isinstance(roles, list):
        roles = [str(r).strip().lower() for r in roles if str(r).strip()]
    else:
        roles = []

    # Si faltan roles, intentamos consultarlos
    if not roles and user_id is not None:
        try:
            fetched = _user_svc.list_role_codes(int(user_id)) or []
            if isinstance(fetched, list):
                roles = [str(r).strip().lower() for r in fetched if str(r).strip()]
        except Exception:
            pass

    # Compatibilidad: si existe 'role' simple y no hay lista
    role_single = u.get("role") or u.get("rol")
    if not roles and role_single:
        roles = [str(role_single).strip().lower()]

    u["roles"] = roles
    u["role"] = roles[0] if roles else None
    u["role_display"] = ", ".join(roles) if roles else None
    return u


# ---- Helpers NUEVOS para nombre/nip ----
def _canonize_nombre_nip(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Acepta alias y normaliza a claves canónicas:
    - nombre: name | full_name | fullname -> nombre
    - nip: pin -> nip (en MAYÚSCULAS)
    """
    out = dict(data)
    if out.get("nombre") is None:
        alias_nombre = out.get("full_name") or out.get("fullname") or out.get("name")
        if alias_nombre is not None:
            out["nombre"] = alias_nombre
    if "nip" in out or "pin" in out:
        nip_raw = out.get("nip", out.get("pin"))
        out["nip"] = (str(nip_raw).upper()) if nip_raw is not None else None
    return out


def _validate_nip_if_present(nip: Optional[str]) -> None:
    if nip is None:
        return
    if not NIP_RE.match(nip):
        raise ValueError("El NIP debe tener el formato 5 dígitos, guion y 1 letra mayúscula. Ejemplo: 12345-A")


# ---------- Catálogo de roles para el frontend ----------
@users_bp.get("/roles")
@jwt_required()
def list_allowed_roles():
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    # Intentamos pedir al servicio por si tienes otros roles en BD
    try:
        if hasattr(_user_svc, "list_all_roles"):
            rows = _user_svc.list_all_roles()  # [{"id":..,"code":"admin"}, ...]
            svc_codes = {(r.get("code") or "").strip().lower() for r in rows if r.get("code")}
            codes = sorted((svc_codes | ALLOWED_ROLE_CODES))
            return jsonify({"ok": True, "roles": codes}), 200

        if hasattr(_user_svc, "list_all_role_codes"):
            svc_codes = set(_user_svc.list_all_role_codes() or [])
            codes = sorted((svc_codes | ALLOWED_ROLE_CODES))
            return jsonify({"ok": True, "roles": codes}), 200
    except Exception:
        pass

    # Fallback: los permitidos locales
    return jsonify({"ok": True, "roles": sorted(ALLOWED_ROLE_CODES)}), 200


# --------- Rutas CRUD (sólo admin) ----------

# Listado paginado: GET /users?page=1&size=10&q=texto
@users_bp.get("")
@jwt_required()
def list_users():
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 10))
    except ValueError:
        return jsonify({"ok": False, "msg": "page/size inválidos"}), 400

    page = max(page, 1)
    size = max(1, min(size, 200))
    q = (request.args.get("q") or "").strip().lower()

    # Si tu servicio tiene búsqueda/paginado con roles:
    try:
        data = _user_svc.list_users_with_roles(page=page, size=size, q=q)
        items = list(data.get("items", []))
        # Enriquecer SIEMPRE
        items = [_inject_roles(dict(it)) for it in items]
        total = int(data.get("total", len(items)))
        total_pages = (total + size - 1) // size if size else 1
        return jsonify({"ok": True, "items": items, "total": total, "page": page, "size": size, "total_pages": total_pages}), 200

    except TypeError:
        # fallback si list_users_with_roles no acepta q
        data = _user_svc.list_users_with_roles(page=page, size=size)
        items = list(data.get("items", []))
        if q:
            # ANTES: filtraba solo email. AHORA: email OR nombre OR nip
            filtered = []
            for it in items:
                em = (it.get("email") or "").lower()
                no = (it.get("nombre") or "").lower()
                np = (it.get("nip") or "").lower()
                if q in em or q in no or q in np:
                    filtered.append(it)
            items = filtered
            total = len(items)
            items = [_inject_roles(dict(it)) for it in items]
            return jsonify({"ok": True, "items": items, "total": total, "page": 1, "size": len(items), "total_pages": 1}), 200

        items = [_inject_roles(dict(it)) for it in items]
        total = int(data.get("total", len(items)))
        total_pages = (total + size - 1) // size if size else 1
        return jsonify({"ok": True, "items": items, "total": total, "page": page, "size": size, "total_pages": total_pages}), 200

    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al listar: {e}"}), 500


# Crear usuario: POST /users  {email, password, is_active?, roles?, nombre?, nip?}
@users_bp.post("")
@jwt_required()
def create_user():
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    data = request.get_json(silent=True) or {}
    data = _canonize_nombre_nip(data)

    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    is_active = bool(data.get("is_active", True))
    nombre = (data.get("nombre") or None)
    nip = (data.get("nip") or None)

    if not email or not password:
        return jsonify({"ok": False, "msg": "email y password son requeridos"}), 400

    # Validación estricta de NIP (si viene)
    try:
        _validate_nip_if_present(nip)
    except ValueError as ve:
        return jsonify({"ok": False, "msg": str(ve)}), 400

    # validar roles (si vienen)
    want_roles = data.get("roles")
    valid_roles, invalid_roles = _normalize_roles_payload(want_roles)
    if isinstance(want_roles, list) and invalid_roles:
        return jsonify({"ok": False, "msg": f"roles inválidos: {invalid_roles}"}), 400

    # Duplicados de email
    try:
        if hasattr(_user_svc, "email_exists") and _user_svc.email_exists(email):
            return jsonify({"ok": False, "msg": "el email ya existe"}), 409
        if _user_svc.get_by_email(email):
            return jsonify({"ok": False, "msg": "el email ya existe"}), 409
    except Exception:
        pass

    try:
        user = _user_svc.create_user(
            email=email,
            password=password,
            is_active=is_active,
            nombre=nombre,
            nip=nip,
        )

        # asignar roles válidos al crear
        for rc in valid_roles:
            try:
                _user_svc.assign_role(user["id"], rc)
            except Exception:
                pass

        # devolver con roles si está disponible
        if hasattr(_user_svc, "get_user_with_roles"):
            user = _user_svc.get_user_with_roles(user["id"]) or user

        return jsonify({"ok": True, "user": _inject_roles(dict(user))}), 201

    except Exception as e:
        msg = str(e)
        # --- NUEVO: errores amigables por constraint del NIP ---
        if "ck_users_nip_format" in msg or ("check constraint" in msg and "nip" in msg.lower()):
            return jsonify({"ok": False, "msg": "El NIP debe tener el formato 5 dígitos, guion y 1 letra mayúscula. Ejemplo: 12345-A"}), 400
        if "users_email_key" in msg:
            return jsonify({"ok": False, "msg": "el email ya existe"}), 409
        if "ux_users_nip" in msg:
            return jsonify({"ok": False, "msg": "el NIP ya existe"}), 409
        return jsonify({"ok": False, "msg": f"error al crear: {e}"}), 500


# Obtener usuario: GET /users/<id>
@users_bp.get("/<int:user_id>")
@jwt_required()
def get_user(user_id: int):
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    try:
        # Preferir método que trae roles
        if hasattr(_user_svc, "get_user_with_roles"):
            user = _user_svc.get_user_with_roles(user_id)
        else:
            user = _user_svc.get_by_id(user_id)
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al obtener: {e}"}), 500

    if not user:
        return jsonify({"ok": False, "msg": "no encontrado"}), 404
    return jsonify({"ok": True, "user": _inject_roles(dict(user))}), 200


# Actualizar: PUT /users/<id>  {email?, password?, is_active?, roles?, nombre?, nip?}
@users_bp.put("/<int:user_id>")
@jwt_required()
def update_user(user_id: int):
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    data = request.get_json(silent=True) or {}
    data = _canonize_nombre_nip(data)

    email = (data.get("email") or "").strip().lower() if data.get("email") else None
    password = data.get("password")
    is_active = data.get("is_active")
    if is_active is not None:
        is_active = bool(is_active)
    nombre = data.get("nombre") if "nombre" in data else None
    nip = data.get("nip") if "nip" in data else None

    # Validación estricta de NIP si lo envían
    try:
        _validate_nip_if_present(nip)
    except ValueError as ve:
        return jsonify({"ok": False, "msg": str(ve)}), 400

    # validar roles (si vienen)
    want_roles = data.get("roles")
    valid_roles, invalid_roles = _normalize_roles_payload(want_roles)
    if isinstance(want_roles, list) and invalid_roles:
        return jsonify({"ok": False, "msg": f"roles inválidos: {invalid_roles}"}), 400

    # si cambia email, validar duplicado contra otro usuario
    if email:
        try:
            if hasattr(_user_svc, "email_exists") and _user_svc.email_exists(email):
                existing = _user_svc.get_by_email(email)
                if existing and existing["id"] != user_id:
                    return jsonify({"ok": False, "msg": "el email ya existe"}), 409
            else:
                existing = _user_svc.get_by_email(email)
                if existing and existing["id"] != user_id:
                    return jsonify({"ok": False, "msg": "el email ya existe"}), 409
        except Exception:
            pass

    try:
        updated = _user_svc.update_user(
            user_id,
            email=email,
            password=password,
            is_active=is_active,
            nombre=nombre,
            nip=nip,
        )
    except Exception as e:
        msg = str(e)
        # --- NUEVO: errores amigables por constraint del NIP ---
        if "ck_users_nip_format" in msg or ("check constraint" in msg and "nip" in msg.lower()):
            return jsonify({"ok": False, "msg": "El NIP debe tener el formato 5 dígitos, guion y 1 letra mayúscula. Ejemplo: 12345-A"}), 400
        if "users_email_key" in msg:
            return jsonify({"ok": False, "msg": "el email ya existe"}), 409
        if "ux_users_nip" in msg:
            return jsonify({"ok": False, "msg": "el NIP ya existe"}), 409
        return jsonify({"ok": False, "msg": f"error al actualizar: {e}"}), 500

    if not updated:
        return jsonify({"ok": False, "msg": "no encontrado"}), 404

    # actualizar roles si envías roles: string[]
    if isinstance(want_roles, list):
        try:
            actuales = set(_user_svc.list_role_codes(user_id) or [])
            nuevos = set(valid_roles)
            # revocar los que ya no están
            for rc in actuales - nuevos:
                try:
                    _user_svc.revoke_role(user_id, rc)
                except Exception:
                    pass
            # asignar los nuevos
            for rc in nuevos - actuales:
                try:
                    _user_svc.assign_role(user_id, rc)
                except Exception:
                    pass
            # refrescar usuario con roles si existe el método
            if hasattr(_user_svc, "get_user_with_roles"):
                updated = _user_svc.get_user_with_roles(user_id) or updated
        except Exception:
            # si no hay soporte de roles, no rompemos
            pass

    return jsonify({"ok": True, "user": _inject_roles(dict(updated))}), 200


# Eliminar: DELETE /users/<id>
@users_bp.delete("/<int:user_id>")
@jwt_required()
def delete_user(user_id: int):
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    try:
        ok = _user_svc.delete_user(user_id)
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al eliminar: {e}"}), 500

    if not ok:
        return jsonify({"ok": False, "msg": "no encontrado"}), 404
    return jsonify({"ok": True}), 200


# --------- Extras útiles ---------

# Cambiar contraseña (propietario o admin):
# PUT /users/<id>/password {password: "..."}
@users_bp.put("/<int:user_id>/password")
@jwt_required()
def change_password(user_id: int):
    uid = _current_uid_int()
    if uid is None:
        return jsonify({"ok": False, "msg": "no autorizado"}), 401
    # permitir si es admin o si es el propietario
    if (not _is_admin(uid)) and (uid != user_id):
        return jsonify({"ok": False, "msg": "permiso denegado"}), 403

    data = request.get_json(silent=True) or {}
    new_pass = data.get("password")
    if not new_pass:
        return jsonify({"ok": False, "msg": "password requerido"}), 400

    try:
        updated = _user_svc.update_user(user_id, password=new_pass)
        if not updated:
            return jsonify({"ok": False, "msg": "no encontrado"}), 404
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al cambiar contraseña: {e}"}), 500


# Gestionar roles: PUT /users/<id>/roles {roles: ["admin","patrullero"]}
@users_bp.put("/<int:user_id>/roles")
@jwt_required()
def set_roles(user_id: int):
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    data = request.get_json(silent=True) or {}
    roles = data.get("roles")
    if not isinstance(roles, list):
        return jsonify({"ok": False, "msg": "roles debe ser arreglo de strings"}), 400

    valid_roles, invalid_roles = _normalize_roles_payload(roles)
    if invalid_roles:
        return jsonify({"ok": False, "msg": f"roles inválidos: {invalid_roles}"}), 400

    nuevos = set(valid_roles)

    try:
        actuales = set(_user_svc.list_role_codes(user_id) or [])
        # revocar los que ya no van
        for rc in actuales - nuevos:
            try:
                _user_svc.revoke_role(user_id, rc)
            except Exception:
                pass
        # asignar los nuevos
        for rc in nuevos - actuales:
            try:
                _user_svc.assign_role(user_id, rc)
            except Exception:
                pass
        # devolver usuario + roles si existe el método
        user = (_user_svc.get_user_with_roles(user_id)
                if hasattr(_user_svc, "get_user_with_roles")
                else _user_svc.get_by_id(user_id))
        if not user:
            return jsonify({"ok": False, "msg": "no encontrado"}), 404
        return jsonify({"ok": True, "user": _inject_roles(dict(user))}), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al actualizar roles: {e}"}), 500
