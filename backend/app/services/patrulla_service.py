# backend/app/services/patrulla_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy import text
from flask import current_app


class PatrullaService:
    """
    Servicio fino que usa el engine compartido (current_app.extensions["db_engine"])
    para CRUD sobre la tabla 'patrulla'. Crea la tabla si no existe.
    """

    def _engine(self):
        eng = current_app.extensions.get("db_engine")
        if eng is None:
            raise RuntimeError("DB engine not initialized")
        return eng

    # -------- schema ----------
    def ensure_schema(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS patrulla (
            id          SERIAL PRIMARY KEY,
            codigo      VARCHAR(50) UNIQUE NOT NULL,
            alias       VARCHAR(100),
            placa       VARCHAR(50),
            is_activa   BOOLEAN NOT NULL DEFAULT TRUE,
            created_at  TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """
        with self._engine().begin() as cx:
            cx.execute(text(sql))

    # -------- list ----------
    def list(
        self,
        page: int = 1,
        size: int = 10,
        q: str = "",
    ) -> Dict[str, Any]:
        page = max(int(page or 1), 1)
        size = max(min(int(size or 10), 200), 1)
        off = (page - 1) * size

        params = {}
        where = ""
        if q:
            where = "WHERE (LOWER(codigo) LIKE :q OR LOWER(alias) LIKE :q OR LOWER(placa) LIKE :q)"
            params["q"] = f"%{q.lower()}%"

        sql_count = f"SELECT COUNT(*) FROM patrulla {where};"
        sql_rows = f"""
        SELECT id, codigo, alias, placa, is_activa, created_at
        FROM patrulla
        {where}
        ORDER BY id DESC
        LIMIT :size OFFSET :off;
        """

        with self._engine().begin() as cx:
            total = cx.execute(text(sql_count), params).scalar() or 0
            rows = cx.execute(
                text(sql_rows),
                {**params, "size": size, "off": off},
            ).mappings().all()

        items = [dict(r) for r in rows]
        return {"items": items, "page": page, "size": size, "total": total}

    # -------- get ----------
    def get(self, pid: int) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT id, codigo, alias, placa, is_activa, created_at
        FROM patrulla WHERE id = :id;
        """
        with self._engine().begin() as cx:
            r = cx.execute(text(sql), {"id": pid}).mappings().first()
        return dict(r) if r else None

    # -------- create ----------
    def create(self, codigo: str, alias: Optional[str], placa: Optional[str], is_activa: bool = True) -> Dict[str, Any]:
        sql = """
        INSERT INTO patrulla (codigo, alias, placa, is_activa)
        VALUES (:codigo, :alias, :placa, :is_activa)
        RETURNING id, codigo, alias, placa, is_activa, created_at;
        """
        with self._engine().begin() as cx:
            r = cx.execute(
                text(sql),
                {"codigo": codigo, "alias": alias, "placa": placa, "is_activa": bool(is_activa)},
            ).mappings().first()
        return dict(r)

    # -------- update ----------
    def update(
        self,
        pid: int,
        *,
        codigo: Optional[str] = None,
        alias: Optional[str] = None,
        placa: Optional[str] = None,
        is_activa: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        # build set dynamico
        sets: List[str] = []
        params: Dict[str, Any] = {"id": pid}
        if codigo is not None:
            sets.append("codigo = :codigo")
            params["codigo"] = codigo
        if alias is not None:
            sets.append("alias = :alias")
            params["alias"] = alias
        if placa is not None:
            sets.append("placa = :placa")
            params["placa"] = placa
        if is_activa is not None:
            sets.append("is_activa = :is_activa")
            params["is_activa"] = bool(is_activa)

        if not sets:
            return self.get(pid)

        sql = f"""
        UPDATE patrulla
        SET {", ".join(sets)}
        WHERE id = :id
        RETURNING id, codigo, alias, placa, is_activa, created_at;
        """
        with self._engine().begin() as cx:
            r = cx.execute(text(sql), params).mappings().first()
        return dict(r) if r else None

    # -------- delete ----------
    def delete(self, pid: int) -> bool:
        sql = "DELETE FROM patrulla WHERE id = :id;"
        with self._engine().begin() as cx:
            res = cx.execute(text(sql), {"id": pid})
        return (res.rowcount or 0) > 0
