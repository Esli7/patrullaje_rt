# backend/app/repositories/ubicacion_repository.py
from typing import Any, Dict, List, Optional
from psycopg.rows import dict_row  # si tu adapter lo soporta (psycopg3)

class UbicacionRepository:
    def __init__(self, db):
        """
        db es el adapter/connection que guardaste en app.extensions["db"] en create_app()
        """
        self.db = db

    def listar(self) -> List[Dict[str, Any]]:
        """
        Devuelve las ubicaciones más recientes. Ajusta la tabla/columnas a tu esquema real.
        """
        try:
            with self.db.cursor(row_factory=dict_row) as cur:
                cur.execute("""
                    SELECT id,
                           patrulla,
                           lat,
                           lng,
                           estado,
                           updated_at AS ts
                    FROM ubicaciones
                    ORDER BY updated_at DESC
                    LIMIT 200
                """)
                return cur.fetchall()
        except Exception:
            # Si aún no tienes la tabla, evita tumbar el backend.
            return []

    def crear(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inserta una ubicación. Ajusta columnas a tu esquema real.
        """
        with self.db.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                INSERT INTO ubicaciones (patrulla, lat, lng, estado)
                VALUES (%s, %s, %s, %s)
                RETURNING id, patrulla, lat, lng, estado, updated_at AS ts
            """, (data.get("patrulla"), data.get("lat"), data.get("lng"), data.get("estado")))
            row = cur.fetchone()
            self.db.commit()
            return row

    def obtener(self, ubicacion_id: int) -> Optional[Dict[str, Any]]:
        with self.db.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT id, patrulla, lat, lng, estado, updated_at AS ts
                FROM ubicaciones
                WHERE id = %s
            """, (ubicacion_id,))
            return cur.fetchone()
