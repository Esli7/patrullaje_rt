# backend/app/endpoints/mobile.py
from __future__ import annotations

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import text

mobile_bp = Blueprint("mobile", __name__)

# ---------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------
def _get_engine():
    eng = current_app.extensions.get("db_engine")
    if not eng:
        raise RuntimeError("DB engine no disponible")
    return eng


# ---------------------------------------------------------------------
# GET /api/mobile/patrullas  (ya lo tenías)
# ---------------------------------------------------------------------
@mobile_bp.get("/patrullas")
@jwt_required()  # ← protegido: la app móvil ya va autenticada
def listar_patrullas_mobile():
    """
    Lista patrullas para la app móvil, con solo los campos mínimos.
    Soporta:
      - q: búsqueda por alias o código (ILIKE)
      - page, size: paginación (size máx 200)
    Respuesta:
      { ok, items: [{id, codigo, alias}], page, size, total }
    """
    q = (request.args.get("q") or "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
        size = int(request.args.get("size", 100))
    except ValueError:
        return jsonify({"ok": False, "msg": "page/size inválidos"}), 400

    size = max(1, min(size, 200))
    off = (page - 1) * size

    # Filtro por búsqueda (alias/codigo)
    where = """
        WHERE (:q = '' OR
               COALESCE(p.alias,'')  ILIKE '%' || :q || '%' OR
               COALESCE(p.codigo,'') ILIKE '%' || :q || '%')
    """

    # Conteo total
    sql_count = text(f"SELECT COUNT(*) FROM patrulla p {where}")

    # Datos paginados (solo campos mínimos)
    sql_items = text(f"""
        SELECT p.id, p.codigo, p.alias
          FROM patrulla p
          {where}
         ORDER BY NULLIF(p.alias, '') IS NULL, p.alias ASC, p.codigo ASC
         LIMIT :lim OFFSET :off
    """)

    eng = _get_engine()
    try:
        with eng.connect() as conn:
            total = conn.execute(sql_count, {"q": q}).scalar() or 0
            rows = conn.execute(sql_items, {"q": q, "lim": size, "off": off}).fetchall()
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al listar patrullas: {e}"}), 500

    items = [{"id": r[0], "codigo": r[1], "alias": r[2]} for r in rows]

    return jsonify({
        "ok": True,
        "items": items,
        "page": page,
        "size": size,
        "total": total
    }), 200


# ---------------------------------------------------------------------
# GET /api/mobile/asignacion  (NUEVO)
# Devuelve la asignación activa del usuario autenticado con payload mínimo.
# Respuesta: { ok, asignacion: { patrulla_id, alias, codigo } | null }
# ---------------------------------------------------------------------
@mobile_bp.get("/asignacion")
@jwt_required()
def asignacion_actual_mobile():
    uid_raw = get_jwt_identity()
    try:
        uid = int(uid_raw) if uid_raw is not None else None
    except Exception:
        uid = None

    if uid is None:
        return jsonify({"ok": False, "msg": "Usuario inválido en JWT"}), 401

    eng = _get_engine()
    try:
        with eng.connect() as conn:
            # Preferimos la tabla nueva user_patrulla_asignacion (una activa por usuario)
            pid = conn.execute(
                text("""
                    SELECT patrulla_id
                      FROM user_patrulla_asignacion
                     WHERE user_id = :uid AND ended_at IS NULL
                     ORDER BY started_at DESC
                     LIMIT 1
                """),
                {"uid": uid},
            ).scalar()

            if not pid:
                # Sin asignación activa
                return jsonify({"ok": True, "asignacion": None}), 200

            row = conn.execute(
                text("SELECT id, alias, codigo FROM patrulla WHERE id = :pid"),
                {"pid": pid},
            ).fetchone()

            if not row:
                return jsonify({"ok": True, "asignacion": None}), 200

            asignacion = {
                "patrulla_id": row[0],
                "alias": row[1],
                "codigo": row[2],
            }
            return jsonify({"ok": True, "asignacion": asignacion}), 200

    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al consultar asignación: {e}"}), 500
