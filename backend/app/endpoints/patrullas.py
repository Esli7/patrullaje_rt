# backend/app/endpoints/patrullas.py
from __future__ import annotations

from typing import Optional, Tuple
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.services.patrulla_service import PatrullaService
from app.services.user_service import UserService

patrullas_bp = Blueprint("patrullas", __name__)
_patr_svc = PatrullaService()
_user_svc = UserService()


@patrullas_bp.record_once
def _ensure_schema(_state):
    # Crea la tabla 'patrulla' si no existe
    try:
        _patr_svc.ensure_schema()
    except Exception as e:
        print(f"[patrullas] ensure_schema warning: {e}")


# ------- helpers de admin -------
def _current_uid_int() -> Optional[int]:
    try:
        val = get_jwt_identity()
        return int(val) if val is not None else None
    except Exception:
        return None


def _is_admin(uid: Optional[int]) -> bool:
    if not uid:
        return False
    try:
        roles = _user_svc.list_role_codes(uid) or []
        return "admin" in roles
    except Exception:
        return False


def _admin_guard() -> Optional[Tuple[dict, int]]:
    uid = _current_uid_int()
    if uid is None:
        return {"ok": False, "msg": "no autorizado"}, 401
    if not _is_admin(uid):
        return {"ok": False, "msg": "permiso denegado"}, 403
    return None


# ------- rutas CRUD (solo admin) -------

# GET /api/patrullas?page=1&size=10&q=abc
@patrullas_bp.get("")
@jwt_required()
def list_patrullas():
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 10))
    except ValueError:
        return jsonify({"ok": False, "msg": "page/size inválidos"}), 400
    q = (request.args.get("q") or "").strip()

    try:
        data = _patr_svc.list(page=page, size=size, q=q)
        total = int(data.get("total", 0))
        total_pages = (total + size - 1) // size if size else 1
        return jsonify({**data, "ok": True, "total_pages": total_pages}), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al listar: {e}"}), 500


# POST /api/patrullas  {codigo, alias?, placa?, is_activa?}
@patrullas_bp.post("")
@jwt_required()
def create_patrulla():
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    data = request.get_json(silent=True) or {}
    codigo = (data.get("codigo") or "").strip()
    alias = (data.get("alias") or "").strip() or None
    placa = (data.get("placa") or "").strip() or None
    is_activa = bool(data.get("is_activa", True))

    if not codigo:
        return jsonify({"ok": False, "msg": "codigo requerido"}), 400

    try:
        item = _patr_svc.create(codigo=codigo, alias=alias, placa=placa, is_activa=is_activa)
        return jsonify({"ok": True, "patrulla": item}), 201
    except Exception as e:
        # posible duplicado de codigo (unique)
        return jsonify({"ok": False, "msg": f"error al crear: {e}"}), 500


# GET /api/patrullas/<id>
@patrullas_bp.get("/<int:pid>")
@jwt_required()
def get_patrulla(pid: int):
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    try:
        item = _patr_svc.get(pid)
        if not item:
            return jsonify({"ok": False, "msg": "no encontrado"}), 404
        return jsonify({"ok": True, "patrulla": item}), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al obtener: {e}"}), 500


# PUT /api/patrullas/<id>  {codigo?, alias?, placa?, is_activa?}
@patrullas_bp.put("/<int:pid>")
@jwt_required()
def update_patrulla(pid: int):
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    data = request.get_json(silent=True) or {}
    codigo = data.get("codigo")
    alias = data.get("alias")
    placa = data.get("placa")
    is_activa = data.get("is_activa")

    try:
        item = _patr_svc.update(
            pid,
            codigo=(codigo.strip() if isinstance(codigo, str) else codigo),
            alias=(alias.strip() if isinstance(alias, str) else alias),
            placa=(placa.strip() if isinstance(placa, str) else placa),
            is_activa=(bool(is_activa) if is_activa is not None else None),
        )
        if not item:
            return jsonify({"ok": False, "msg": "no encontrado"}), 404
        return jsonify({"ok": True, "patrulla": item}), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al actualizar: {e}"}), 500


# DELETE /api/patrullas/<id>
@patrullas_bp.delete("/<int:pid>")
@jwt_required()
def delete_patrulla(pid: int):
    guard = _admin_guard()
    if guard:
        body, code = guard
        return jsonify(body), code

    try:
        ok = _patr_svc.delete(pid)
        if not ok:
            return jsonify({"ok": False, "msg": "no encontrado"}), 404
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al eliminar: {e}"}), 500
