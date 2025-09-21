# backend/app/endpoints/ubicaciones.py
from flask import Blueprint, jsonify, request, current_app
from app.controllers.ubicaciones_controller import UbicacionesController
from app.services.ubicacion_service import UbicacionService
from app.repositories.ubicacion_repository import UbicacionRepository

ubic_bp = Blueprint("ubicaciones", __name__)

def get_ctrl() -> UbicacionesController:
    db = current_app.extensions["db"]           # <- conexión creada en create_app()
    repo = UbicacionRepository(db)
    service = UbicacionService(repo)
    return UbicacionesController(service)

@ubic_bp.get("/ubicaciones")
def listar_ubicaciones():
    return jsonify(get_ctrl().listar())

@ubic_bp.post("/ubicaciones")
def crear_ubicacion():
    data = request.get_json(force=True, silent=True) or {}
    return jsonify(get_ctrl().crear(data)), 201
