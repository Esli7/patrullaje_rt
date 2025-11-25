# backend/app/endpoints/ubicaciones.py
from __future__ import annotations

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from sqlalchemy import text

from app.controllers.ubicaciones_controller import UbicacionesController

# Nota: SIN url_prefix aquí. El prefijo final se fija en app/__init__.py al registrar.
ubic_bp = Blueprint("ubicaciones", __name__)

_ctrl: UbicacionesController | None = None


def get_ctrl() -> UbicacionesController:
    """Singleton simple del controller para no recrearlo en cada request."""
    global _ctrl
    if _ctrl is None:
        _ctrl = UbicacionesController()
    return _ctrl


@ubic_bp.record_once
def _ensure_schema(_state):
    """Crea/asegura el esquema al registrar el blueprint (no tumba si ya existe)."""
    try:
        get_ctrl().ensure_schema()
    except Exception as e:
        print(f"[ubicaciones] ensure_schema warning: {e}")


# ---------- Helpers de DB ----------
def _table_exists(conn, table_name: str) -> bool:
    """Verifica si existe public.<table_name> usando to_regclass (ignora schema search_path)."""
    q = text("SELECT to_regclass(:tbl) IS NOT NULL")
    return bool(conn.execute(q, {"tbl": f"public.{table_name}"}).scalar())


def _auto_nombre_from_patrulla(patrulla_id) -> str | None:
    """
    Si hay patrulla_id válido, devuelve alias o código de esa patrulla.
    Retorna None si no se puede.
    """
    if patrulla_id in (None, "", 0, "0"):
        return None
    try:
        pid = int(patrulla_id)
    except (TypeError, ValueError):
        return None

    engine = current_app.extensions.get("db_engine")
    if not engine:
        return None

    sql = text(
        "SELECT COALESCE(NULLIF(alias,''), NULLIF(codigo,'')) "
        "FROM patrulla WHERE id = :pid"
    )
    try:
        with engine.connect() as conn:
            val = conn.execute(sql, {"pid": pid}).scalar()
        return val
    except Exception:
        return None


# ---------- Resolver principal: patrulla activa para el usuario del JWT ----------
def _resolve_patrulla_for_user() -> tuple[int | None, dict | None]:
    """
    Devuelve (patrulla_id, {'id','alias','codigo'} | None) para el usuario autenticado.

    Prioridad:
      1) NUEVO: user_patrulla_asignacion (ended_at IS NULL) por user_id.
      2) Fallback: operador/asignacion_patrulla (activo=true o ventana inicio/fin).

    Si nada aplica, retorna (None, None).
    """
    engine = current_app.extensions.get("db_engine")
    if engine is None:
        return None, None

    claims = get_jwt() or {}
    email = (claims.get("email") or "").strip().lower()
    uid = get_jwt_identity()
    try:
        uid_int = int(uid) if uid is not None else None
    except Exception:
        uid_int = None

    if uid_int is None and not email:
        return None, None

    with engine.connect() as conn:
        # 1) Preferir la tabla nueva si existe
        try:
            if uid_int is not None and _table_exists(conn, "user_patrulla_asignacion"):
                row = conn.execute(
                    text(
                        """
                        SELECT p.id, p.alias, p.codigo
                          FROM user_patrulla_asignacion a
                          JOIN patrulla p ON p.id = a.patrulla_id
                         WHERE a.user_id = :uid AND a.ended_at IS NULL
                         ORDER BY a.started_at DESC
                         LIMIT 1
                        """
                    ),
                    {"uid": uid_int},
                ).fetchone()
                if row:
                    pid, alias, codigo = row[0], row[1], row[2]
                    return pid, {"id": pid, "alias": alias, "codigo": codigo}
        except Exception:
            # No interrumpir el flujo: caer al fallback
            pass

        # 2) Fallback de compatibilidad: operador/asignacion_patrulla si existen
        try:
            if _table_exists(conn, "operador") and _table_exists(conn, "asignacion_patrulla"):
                row = conn.execute(
                    text(
                        """
                        WITH op AS (
                          SELECT o.id
                          FROM operador o
                          WHERE (:email <> '' AND LOWER(o.email) = :email)
                          UNION
                          SELECT o2.id
                          FROM operador o2
                          WHERE (:uid::bigint IS NOT NULL)
                            AND EXISTS (
                              SELECT 1 FROM pg_catalog.pg_attribute
                              WHERE attrelid = 'operador'::regclass
                                AND attname = 'user_id'
                                AND NOT attisdropped
                            )
                            AND o2.user_id = :uid::bigint
                          LIMIT 1
                        ),
                        asign AS (
                          SELECT ap.patrulla_id
                          FROM asignacion_patrulla ap
                          JOIN op ON op.id = ap.operador_id
                          WHERE
                            (
                              EXISTS (
                                SELECT 1 FROM pg_catalog.pg_attribute
                                WHERE attrelid = 'asignacion_patrulla'::regclass
                                  AND attname = 'activo'
                                  AND NOT attisdropped
                              ) AND ap.activo = TRUE
                            )
                            OR
                            (
                              EXISTS (
                                SELECT 1 FROM pg_catalog.pg_attribute
                                WHERE attrelid = 'asignacion_patrulla'::regclass
                                  AND attname = 'inicio'
                                  AND NOT attisdropped
                              )
                              AND ap.inicio <= NOW()
                              AND (
                                NOT EXISTS (
                                  SELECT 1 FROM pg_catalog.pg_attribute
                                  WHERE attrelid = 'asignacion_patrulla'::regclass
                                    AND attname = 'fin'
                                    AND NOT attisdropped
                                )
                                OR ap.fin IS NULL
                                OR ap.fin >= NOW()
                              )
                            )
                          ORDER BY ap.inicio DESC NULLS LAST, ap.id DESC
                          LIMIT 1
                        )
                        SELECT p.id, p.alias, p.codigo
                        FROM patrulla p
                        JOIN asign a ON a.patrulla_id = p.id
                        LIMIT 1
                        """
                    ),
                    {"email": email, "uid": uid_int},
                ).fetchone()
                if row:
                    pid, alias, codigo = row[0], row[1], row[2]
                    return pid, {"id": pid, "alias": alias, "codigo": codigo}
        except Exception:
            pass

    return None, None


# -------------------------
# Crear (PROTEGIDO)
# -------------------------
@ubic_bp.post("")
@jwt_required()  # ← requiere sesión (cookie httpOnly o Bearer, según tu config)
def crear_ubicacion():
    data = request.get_json(silent=True) or {}

    # 1) Resolver patrulla por asignación activa del usuario (y fallback)
    resolved_pid, pinfo = _resolve_patrulla_for_user()

    # 2) Si el cliente envía patrulla_id, úsalo sólo si no resolvimos antes
    patrulla_id = resolved_pid or data.get("patrulla_id")

    if not patrulla_id:
        return (
            jsonify(
                {
                    "ok": False,
                    "msg": (
                        "No se pudo resolver una patrulla activa para el usuario y tampoco recibimos patrulla_id. "
                        "Abre una asignación en /api/asignaciones/start o envía patrulla_id para pruebas."
                    ),
                }
            ),
            422,
        )

    data["patrulla_id"] = patrulla_id

    # 3) 'nombre' opcional con autocompletado por alias/código
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        if pinfo and (pinfo.get("alias") or pinfo.get("codigo")):
            data["nombre"] = pinfo.get("alias") or pinfo.get("codigo")
        else:
            auto = _auto_nombre_from_patrulla(patrulla_id)
            data["nombre"] = auto or f"Patrulla {patrulla_id}"

    try:
        row = get_ctrl().crear(data)
        return jsonify(row), 201
    except ValueError as ve:
        return jsonify({"ok": False, "msg": str(ve)}), 400
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al crear: {e}"}), 500


# -------------------------
# Listar: por bbox o paginado (PÚBLICO por ahora)
# -------------------------
@ubic_bp.get("")
def listar_ubicaciones():
    bbox = request.args.get("bbox")
    if bbox:
        try:
            items = get_ctrl().listar_bbox(bbox)
            return jsonify(items), 200
        except Exception as e:
            return jsonify({"ok": False, "msg": f"bbox inválido: {e}"}), 400

    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", 100))
    except ValueError:
        return jsonify({"ok": False, "msg": "page/size inválidos"}), 400

    try:
        data = get_ctrl().listar(page=page, size=size)
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al listar: {e}"}), 500


# -------------------------
# Obtener uno (PÚBLICO por ahora)
# -------------------------
@ubic_bp.get("/<int:ubic_id>")
def obtener_ubicacion(ubic_id: int):
    try:
        row = get_ctrl().obtener(ubic_id)
        if not row:
            return jsonify({"ok": False, "msg": "no encontrado"}), 404
        return jsonify(row), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al obtener: {e}"}), 500


# -------------------------
# Actualizar (PROTEGIDO)
# -------------------------
@ubic_bp.put("/<int:ubic_id>")
@jwt_required()  # ← requiere sesión
def actualizar_ubicacion(ubic_id: int):
    data = request.get_json(silent=True) or {}
    try:
        row = get_ctrl().actualizar(ubic_id, data)
        if not row:
            return jsonify({"ok": False, "msg": "no encontrado"}), 404
        return jsonify(row), 200
    except ValueError as ve:
        return jsonify({"ok": False, "msg": str(ve)}), 400
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al actualizar: {e}"}), 500


# -------------------------
# Eliminar (PROTEGIDO)
# -------------------------
@ubic_bp.delete("/<int:ubic_id>")
@jwt_required()  # ← requiere sesión
def eliminar_ubicacion(ubic_id: int):
    try:
        ok = get_ctrl().eliminar(ubic_id)
        if not ok:
            return jsonify({"ok": False, "msg": "no encontrado"}), 404
        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error al eliminar: {e}"}), 500


# -------------------------
# GeoJSON / Geo (PÚBLICO por ahora)
# -------------------------
@ubic_bp.get("/geo")
def geo_feature_collection():
    """
    Devuelve un FeatureCollection GeoJSON listo para Leaflet/Mapbox.

    Soporta query params:
      - limit: int (por defecto 1000)
      - patrulla_id: int (opcional)
      - desde/hasta: ISO8601 o 'YYYY-MM-DD HH:MM:SS'
      - bbox: 'minLng,minLat,maxLng,maxLat' (opcional)
    """
    # --- limit robusto
    try:
        limit = int(request.args.get("limit", 1000))
    except ValueError:
        limit = 1000
    limit = max(1, min(limit, 5000))

    # --- filtros opcionales
    patrulla_id = request.args.get("patrulla_id")
    try:
        patrulla_id = int(patrulla_id) if patrulla_id not in (None, "") else None
    except Exception:
        return jsonify({"ok": False, "msg": "patrulla_id inválido"}), 400

    desde = request.args.get("desde") or None
    hasta = request.args.get("hasta") or None

    # --- bbox opcional (string o 4 params sueltos)
    bbox = request.args.get("bbox")
    if not bbox:
        min_lng = request.args.get("minLng")
        min_lat = request.args.get("minLat")
        max_lng = request.args.get("maxLng")
        max_lat = request.args.get("maxLat")
        if all(v is not None for v in (min_lng, min_lat, max_lng, max_lat)):
            bbox = f"{min_lng},{min_lat},{max_lng},{max_lat}"

    try:
        fc = get_ctrl().feature_collection(
            patrulla_id=patrulla_id,
            desde=desde,
            hasta=hasta,
            limit=limit,
            bbox=bbox,
        )
        return jsonify(fc), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error en geo: {e}"}), 500


# -------------------------
# Summary (PÚBLICO por ahora)
# -------------------------
@ubic_bp.get("/summary")
def summary():
    try:
        return jsonify(get_ctrl().summary()), 200
    except Exception as e:
        return jsonify({"ok": False, "msg": f"error en summary: {e}"}), 500
