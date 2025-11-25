
from __future__ import annotations

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import text

asig_bp = Blueprint("asignaciones", __name__)

# ---------------------------------------------------------------------
# Helpers de DB
# ---------------------------------------------------------------------
def _engine():
    eng = current_app.extensions.get("db_engine")
    if not eng:
        raise RuntimeError("DB engine no inicializado")
    return eng

def _get_user_by_email(email: str):
    sql = text("""
        SELECT id, email, is_active
          FROM users
         WHERE email = :email
         LIMIT 1
    """)
    with _engine().connect() as conn:
        row = conn.execute(sql, {"email": email}).mappings().first()
        return dict(row) if row else None

def _get_userid_from_jwt() -> tuple[int | None, str | None]:
    """
    Devuelve (user_id, email) a partir del JWT.
    - get_jwt_identity() trae el id que emitimos en /auth/login
    - claims["email"] trae el email
    """
    identity = get_jwt_identity()
    claims = get_jwt() or {}
    email = claims.get("email")
    try:
        uid = int(identity) if identity is not None else None
    except Exception:
        uid = None
    return uid, email


@asig_bp.record_once
def _ensure_schema(_state):
    try:
        with _engine().begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_patrulla_asignacion (
                    id           BIGSERIAL PRIMARY KEY,
                    user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    patrulla_id  INT    NOT NULL REFERENCES patrulla(id) ON DELETE CASCADE,
                    started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    ended_at     TIMESTAMPTZ
                );
            """))
            # Índices
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_upa_user_active
                    ON user_patrulla_asignacion(user_id)
                    WHERE ended_at IS NULL;
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_upa_user_started
                    ON user_patrulla_asignacion(user_id, started_at DESC);
            """))
    except Exception as e:
        print(f"[asignaciones] ensure_schema warning: {e}")

# ---------------------------------------------------------------------
# POST /api/asignaciones/start 
# 
# ---------------------------------------------------------------------
@asig_bp.post("/start")
@jwt_required()
def start_asignacion():
    data = request.get_json(silent=True) or {}
    try:
        patrulla_id = int(data.get("patrulla_id"))
    except Exception:
        return jsonify({"ok": False, "msg": "patrulla_id inválido"}), 400

    uid, email = _get_userid_from_jwt()
    if not uid or not email:
        return jsonify({"ok": False, "msg": "no autorizado"}), 401

    # Veri.. usuario existe/activo
    u = _get_user_by_email(email)
    if not u or not u.get("is_active", True):
        return jsonify({"ok": False, "msg": "usuario inactivo/no existe"}), 401

    # Veri..patrulla existe
    with _engine().connect() as c:
        row = c.execute(text("SELECT id FROM patrulla WHERE id = :pid"), {"pid": patrulla_id}).first()
        if not row:
            return jsonify({"ok": False, "msg": "patrulla no existe"}), 404

    # Cierra asignación activa previa (si la hay) y crea nueva
    now = datetime.now(timezone.utc)
    with _engine().begin() as conn:
        conn.execute(
            text("""
                UPDATE user_patrulla_asignacion
                   SET ended_at = :now
                 WHERE user_id = :uid
                   AND ended_at IS NULL
            """),
            {"now": now, "uid": uid},
        )
        new_row = conn.execute(
            text("""
                INSERT INTO user_patrulla_asignacion (user_id, patrulla_id, started_at)
                VALUES (:uid, :pid, :now)
                RETURNING id, user_id, patrulla_id, started_at, ended_at
            """),
            {"uid": uid, "pid": patrulla_id, "now": now},
        ).mappings().first()

    return jsonify({"ok": True, "asignacion": dict(new_row)}), 201

# ---------------------------------------------------------------------
# POST fin asignación activa
# ---------------------------------------------------------------------
@asig_bp.post("/end")
@jwt_required()
def end_asignacion():
    uid, email = _get_userid_from_jwt()
    if not uid or not email:
        return jsonify({"ok": False, "msg": "no autorizado"}), 401

    now = datetime.now(timezone.utc)
    with _engine().begin() as conn:
        res = conn.execute(
            text("""
                UPDATE user_patrulla_asignacion
                   SET ended_at = :now
                 WHERE user_id = :uid
                   AND ended_at IS NULL
             RETURNING id, user_id, patrulla_id, started_at, ended_at
            """),
            {"uid": uid, "now": now},
        ).mappings().first()

    if not res:
        return jsonify({"ok": False, "msg": "no hay asignación activa"}), 404

    return jsonify({"ok": True, "asignacion": dict(res)}), 200

# ---------------------------------------------------------------------
# GET /api/asignaciones/current
# ---------------------------------------------------------------------
@asig_bp.get("/current")
@jwt_required()
def current_asignacion():
    uid, email = _get_userid_from_jwt()
    if not uid or not email:
        return jsonify({"ok": False, "msg": "no autorizado"}), 401

    with _engine().connect() as conn:
        row = conn.execute(
            text("""
                SELECT a.id, a.user_id, a.patrulla_id, a.started_at, a.ended_at,
                       p.codigo AS patrulla_codigo, p.alias AS patrulla_alias
                  FROM user_patrulla_asignacion a
                  JOIN patrulla p ON p.id = a.patrulla_id
                 WHERE a.user_id = :uid AND a.ended_at IS NULL
                 ORDER BY a.started_at DESC
                 LIMIT 1
            """),
            {"uid": uid},
        ).mappings().first()

    if not row:
        return jsonify({"ok": True, "asignacion": None}), 200

    return jsonify({"ok": True, "asignacion": dict(row)}), 200

# ---------------------------------------------------------------------
# GET /api/asignaciones/historial del usuario
# ---------------------------------------------------------------------
@asig_bp.get("/mine")
@jwt_required()
def mine_asignaciones():
    uid, email = _get_userid_from_jwt()
    if not uid or not email:
        return jsonify({"ok": False, "msg": "no autorizado"}), 401

    try:
        page = max(int(request.args.get("page", 1)), 1)
        size = min(max(int(request.args.get("size", 10)), 1), 100)
    except Exception:
        return jsonify({"ok": False, "msg": "page/size inválidos"}), 400

    off = (page - 1) * size

    with _engine().connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM user_patrulla_asignacion WHERE user_id = :uid"),
            {"uid": uid},
        ).scalar_one()

        rows = conn.execute(
            text("""
                SELECT a.id, a.user_id, a.patrulla_id, a.started_at, a.ended_at,
                       p.codigo AS patrulla_codigo, p.alias AS patrulla_alias
                  FROM user_patrulla_asignacion a
                  JOIN patrulla p ON p.id = a.patrulla_id
                 WHERE a.user_id = :uid
                 ORDER BY a.started_at DESC
                 LIMIT :size OFFSET :off
            """),
            {"uid": uid, "size": size, "off": off},
        ).mappings().all()

    items = [dict(r) for r in rows]
    return jsonify({
        "ok": True,
        "items": items,
        "page": page,
        "size": size,
        "total": total,
        "total_pages": (total + size - 1) // size if size else 1
    }), 200
