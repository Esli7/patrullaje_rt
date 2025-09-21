from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Iterable, Optional

class DatabaseAdapter(ABC):
    """Interfaz unificada para cualquier motor de BD."""

    @abstractmethod
    def connect(self) -> None: ...
    @abstractmethod
    def close(self) -> None: ...
    @abstractmethod
    def execute(self, sql: str, params: Optional[Iterable[Any]] = None) -> None: ...
    @abstractmethod
    def fetchone(self) -> Optional[tuple]: ...
    @abstractmethod
    def fetchall(self) -> list[tuple]: ...
    @abstractmethod
    def commit(self) -> None: ...
    @abstractmethod
    def rollback(self) -> None: ...

    @contextmanager
    def transaction(self):
        """Uso: with db.transaction(): db.execute(...); ..."""
        try:
            yield
            self.commit()
        except Exception:
            self.rollback()
            raise
