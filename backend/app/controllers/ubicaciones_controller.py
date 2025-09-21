# backend/app/controllers/ubicaciones_controller.py
from typing import Any, Dict, List, Optional

class UbicacionesController:
    def __init__(self, service=None):
        if service is None:
            # construcción perezosa, por si se usa fuera de get_ctrl()
            from flask import current_app
            from app.services.ubicacion_service import UbicacionService
            from app.repositories.ubicacion_repository import UbicacionRepository
            db = current_app.extensions["db"]
            service = UbicacionService(UbicacionRepository(db))
        self.service = service

    def listar(self) -> List[Dict[str, Any]]:
        return self.service.listar()

    def crear(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return self.service.crear(data)
