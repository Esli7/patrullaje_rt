# backend/app/controllers/ubicaciones_controller.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.ubicacion_service import UbicacionService


class UbicacionesController:
    def __init__(self) -> None:
        self.service = UbicacionService()

    # -------------------------
    # Infra / bootstrap
    # -------------------------
    def ensure_schema(self) -> None:
        self.service.ensure_schema()

    # -------------------------
    # CRUD
    # -------------------------
    def crear(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.service.crear(data)

    def actualizar(self, ubic_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return self.service.actualizar(ubic_id, data)

    def eliminar(self, ubic_id: int) -> bool:
        return self.service.eliminar(ubic_id)

    def obtener(self, ubic_id: int) -> Optional[Dict[str, Any]]:
        return self.service.obtener(ubic_id)

    def listar(self, page: int = 1, size: int = 100) -> Dict[str, Any]:
        return self.service.listar(page=page, size=size)

    # -------------------------
    # Helpers internos
    # -------------------------
    def _parse_bbox(self, bbox_str: Optional[str]) -> Optional[Dict[str, float]]:
        """
        Convierte 'minLng,minLat,maxLng,maxLat' -> dict o None.
        Lanza ValueError si el formato/valores son inválidos.
        """
        if not bbox_str:
            return None
        parts = [p.strip() for p in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError("bbox debe tener 4 valores: minLng,minLat,maxLng,maxLat")
        try:
            min_lng, min_lat, max_lng, max_lat = [float(x) for x in parts]
        except Exception:
            raise ValueError("bbox inválido: valores no numéricos")
        if min_lng > max_lng or min_lat > max_lat:
            raise ValueError("bbox inválido: min mayor que max")
        # validación básica de rango
        if not (-180 <= min_lng <= 180 and -180 <= max_lng <= 180):
            raise ValueError("bbox inválido: lng fuera de rango")
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("bbox inválido: lat fuera de rango")
        return {
            "min_lng": min_lng,
            "min_lat": min_lat,
            "max_lng": max_lng,
            "max_lat": max_lat,
        }

    # -------------------------
    # Listado por BBOX (tabla)
    # -------------------------
    def listar_bbox(self, bbox: str) -> List[Dict[str, Any]]:
        """
        bbox="minLng,minLat,maxLng,maxLat"
        Si es inválido, devuelve [] (mismo comportamiento que tenías).
        """
        try:
            parsed = self._parse_bbox(bbox)
            if not parsed:
                return []
            return self.service.listar_bbox(
                parsed["min_lng"], parsed["min_lat"], parsed["max_lng"], parsed["max_lat"]
            )
        except Exception:
            # bbox inválido -> lista vacía (compat)
            return []

    # -------------------------
    # Dashboard
    # -------------------------
    def summary(self) -> Dict[str, Any]:
        return self.service.summary()

    # -------------------------
    # GeoJSON para frontend (Leaflet/Mapbox)
    # -------------------------
    def feature_collection(
        self,
        *,
        patrulla_id: Optional[int] = None,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        limit: Optional[int] = None,
        bbox: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Orquesta la generación de GeoJSON. Acepta filtros opcionales:

        - patrulla_id: (compat futura) se ignora si tu tabla no la tiene.
        - desde/hasta: ISO8601 o 'YYYY-MM-DD HH:MM:SS' contra updated_at.
        - limit: tope de puntos (default 1000, máx 5000).
        - bbox: string 'minLng,minLat,maxLng,maxLat'.

        Retorna FeatureCollection lista para el frontend.
        """
        # normalizar limit
        lim = 1000
        if limit is not None:
            try:
                lim = int(limit)
            except Exception:
                lim = 1000

        # parseo de bbox string -> dict (si viene)
        bbox_dict = None
        if bbox:
            bbox_dict = self._parse_bbox(bbox)

        return self.service.feature_collection(
            patrulla_id=patrulla_id,
            desde=desde,
            hasta=hasta,
            limit=lim,
            bbox=bbox_dict,
        )
