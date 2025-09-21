from typing import Any, Dict, List, Optional

class UbicacionService:
    def listar(self) -> List[Dict[str, Any]]:
        # stub: sin DB aún
        return []

    def crear(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # stub: solo devuelve lo recibido
        return data

    def obtener(self, ubicacion_id: int) -> Optional[Dict[str, Any]]:
        return None
