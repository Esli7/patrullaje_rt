# backend/app/services/ubicacion_service.py
from typing import Any, Dict, List, Optional
from flask import current_app
from app.repositories.ubicacion_repository import UbicacionRepository

class UbicacionService:
    def __init__(self, repo: Optional[UbicacionRepository] = None):
        if repo is None:
            db = current_app.extensions["db"]     # fallback seguro si llamas desde request/app ctx
            repo = UbicacionRepository(db)
        self.repo = repo

    def listar(self, limite: int = 50) -> List[Dict[str, Any]]:
        rows = self.repo.listar()  # o tu método real con límite
        data: List[Dict[str, Any]] = []
        for r in rows:
            data.append({
                "id": r["id"],
                "patrulla": r["patrulla"],
                "lat": float(r["lat"]) if r["lat"] is not None else None,
                "lng": float(r["lng"]) if r["lng"] is not None else None,
                "estado": r.get("estado", "activa"),
                "ts": r.get("ts"),
            })
        return data

    def crear(self, data: Dict[str, Any]) -> Dict[str, Any]:
        row = self.repo.crear(data)
        return {"ok": True, "id": row["id"] if row else None}
