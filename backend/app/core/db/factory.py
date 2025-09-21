from app.core.db.base import DatabaseAdapter
from app.core.db.postgres import PostgresAdapter

def create_adapter(engine: str, **kw) -> DatabaseAdapter:
    if engine.lower() == "postgres":
        return PostgresAdapter(kw["host"], kw["port"], kw["name"], kw["user"], kw["password"])
    raise ValueError(f"Motor no soportado: {engine}")
