# backend/app/services/ubicacion_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import create_engine, text
from flask import current_app

from app.repositories.ubicacion_repository import UbicacionRepository


class UbicacionService:
    def __init__(self) -> None:
        # El repo maneja su propia conexión psycopg (lee Settings.*)
        self.repo = UbicacionRepository()

    def ensure_schema(self) -> None:
        self.repo.ensure_schema()

    # --- validaciones básicas ---
    def _clean_payload(self, data: Dict[str, Any]) -> Tuple[str, float, float, bool]:
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            raise ValueError("nombre es requerido")

        # lat/lng obligatorios + casting
        try:
            lat = float(data["lat"])
            lng = float(data["lng"])
        except Exception:
            raise ValueError("lat/lng inválidos")

        # rangos válidos
        if not (-90.0 <= lat <= 90.0):
            raise ValueError("lat fuera de rango (-90..90)")
        if not (-180.0 <= lng <= 180.0):
            raise ValueError("lng fuera de rango (-180..180)")

        activo = bool(data.get("activo", True))
        return nombre, lat, lng, activo

    # --- operaciones CRUD existentes ---
    def crear(self, data: Dict[str, Any]) -> Dict[str, Any]:
        nombre, lat, lng, activo = self._clean_payload(data)
        row = self.repo.crear({"nombre": nombre, "lat": lat, "lng": lng, "activo": activo})
        return row

    def actualizar(self, ubic_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        nombre = data.get("nombre")
        lat = data.get("lat")
        lng = data.get("lng")
        activo = data.get("activo")
        # castear si vienen
        if lat is not None:
            lat = float(lat)
            if not (-90.0 <= lat <= 90.0):
                raise ValueError("lat fuera de rango (-90..90)")
        if lng is not None:
            lng = float(lng)
            if not (-180.0 <= lng <= 180.0):
                raise ValueError("lng fuera de rango (-180..180)")
        if activo is not None:
            activo = bool(activo)
        return self.repo.actualizar(
            ubic_id,
            nombre=nombre,
            lat=lat,
            lng=lng,
            activo=activo,
        )

    def eliminar(self, ubic_id: int) -> bool:
        return self.repo.eliminar(ubic_id)

    def obtener(self, ubic_id: int) -> Optional[Dict[str, Any]]:
        return self.repo.obtener(ubic_id)

    def listar(self, page: int = 1, size: int = 100) -> Dict[str, Any]:
        return self.repo.listar_paginado(page=page, size=size)

    def listar_bbox(self, min_lng: float, min_lat: float, max_lng: float, max_lat: float) -> List[Dict[str, Any]]:
        # validación ligera
        if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
            raise ValueError("lat bbox fuera de rango")
        if not (-180.0 <= min_lng <= 180.0 and -180.0 <= max_lng <= 180.0):
            raise ValueError("lng bbox fuera de rango")
        if min_lng > max_lng or min_lat > max_lat:
            raise ValueError("bbox inválido: min mayor que max")
        return self.repo.listar_bbox(min_lng, min_lat, max_lng, max_lat)

    # --- para dashboard ---
    def summary(self) -> Dict[str, Any]:
        return {
            "total": self.repo.contar_total(),
            "activas": self.repo.contar_activas(),
            "ultima_actualizacion": self.repo.ultima_actualizacion_iso(),
            "recientes": self.repo.recientes(limit=20),
        }

    # =========================
    #  GeoJSON para Leaflet (sin PostGIS)
    # =========================
    def _engine(self):
        """
        Toma el engine SQLAlchemy inicializado en la app (ver create_app()).
        """
        eng = current_app.extensions.get("db_engine")
        if eng is None:
            # fallback: crear on-demand (no recomendado en hot path)
            from app.config.settings import Settings, build_sqlalchemy_uri
            uri = build_sqlalchemy_uri(Settings)
            eng = create_engine(uri, pool_pre_ping=True)
            current_app.extensions["db_engine"] = eng
        return eng

    def _parse_dt(self, s: str) -> datetime:
        """
        Acepta 'YYYY-MM-DD HH:MM:SS' o ISO 'YYYY-MM-DDTHH:MM:SS'.
        """
        s = (s or "").strip()
        if not s:
            raise ValueError("fecha vacía")
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return datetime.fromisoformat(s.replace(" ", "T"))

    def feature_collection(
        self,
        patrulla_id: Optional[int] = None,   # (no existe en la tabla actual; se devuelve como null)
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        limit: int = 1000,
        bbox: Optional[str] = None,          # <- string "minLng,minLat,maxLng,maxLat"
    ) -> Dict[str, Any]:
        """
        Devuelve un FeatureCollection GeoJSON usando columnas lat/lng de
        public.ubicaciones (sin requerir PostGIS).

        Filtros:
          - desde/hasta: comparan contra updated_at (datetime o string ISO)
          - bbox: 'minLng,minLat,maxLng,maxLat'
          - limit: tope (1..5000)
        """
        # sanitizar limit
        try:
            limit = int(limit)
        except Exception:
            limit = 1000
        limit = max(1, min(limit, 5000))

        conds: List[str] = []
        params: Dict[str, Any] = {"limit": limit}

        # Filtros de tiempo sobre updated_at (SIN ::timestamptz)
        if desde:
            try:
                params["desde"] = self._parse_dt(desde)
                conds.append("u.updated_at >= :desde")
            except Exception:
                pass
        if hasta:
            try:
                params["hasta"] = self._parse_dt(hasta)
                conds.append("u.updated_at <= :hasta")
            except Exception:
                pass

        # BBOX opcional: "minLng,minLat,maxLng,maxLat"
        if bbox:
            try:
                min_lng, min_lat, max_lng, max_lat = [float(x) for x in bbox.split(",")]
                if min_lng > max_lng or min_lat > max_lat:
                    raise ValueError("bbox inválido (min > max)")
                conds.append("u.lng BETWEEN :min_lng AND :max_lng")
                conds.append("u.lat BETWEEN :min_lat AND :max_lat")
                params.update(
                    {"min_lng": min_lng, "max_lng": max_lng, "min_lat": min_lat, "max_lat": max_lat}
                )
            except Exception:
                # bbox mal formado -> lo ignoramos silenciosamente
                pass

        # patrulla_id no existe en la tabla actual => se ignora (se devuelve null)

        where = ("WHERE " + " AND ".join(conds)) if conds else ""

        # Construimos GeoJSON en el servidor con JSON nativo de PostgreSQL
        sql = text(f"""
            SELECT json_build_object(
                'type','FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type','Feature',
                        'geometry', json_build_object(
                            'type','Point',
                            'coordinates', json_build_array(u.lng, u.lat)
                        ),
                        'properties', json_build_object(
                            'id', u.id,
                            'nombre', u.nombre,
                            'activo', u.activo,
                            'patrulla_id', NULL,
                            'ts', to_char(u.updated_at,'YYYY-MM-DD"T"HH24:MI:SSZ')
                        )
                    )
                ), '[]'::json)
            ) AS fc
            FROM (
                SELECT id, nombre, lat, lng, activo, updated_at
                FROM public.ubicaciones u
                {where}
                ORDER BY updated_at ASC
                LIMIT :limit
            ) u;
        """)
        with self._engine().begin() as conn:
            row = conn.execute(sql, params).first()
            return row[0] if row and row[0] else {"type": "FeatureCollection", "features": []}
