# backend/app/services/user_service.py
from typing import Optional, Dict, Any
import psycopg
from werkzeug.security import generate_password_hash, check_password_hash
from app.config.settings import Settings

class UserService:
    def __init__(self):
        self.dsn = (
            f"host={Settings.DB_HOST} port={Settings.DB_PORT} "
            f"dbname={Settings.DB_NAME} user={Settings.DB_USER} password={Settings.DB_PASSWORD}"
        )

    def ensure_schema(self):
        sql = """
        CREATE TABLE IF NOT EXISTS users (
          id BIGSERIAL PRIMARY KEY,
          email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          is_active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                conn.commit()

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT id, email, password_hash, is_active FROM users WHERE email=%s", (email,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "email": row[1],
                "password_hash": row[2],
                "is_active": row[3],
            }

    def create_user(self, email: str, password: str) -> Dict[str, Any]:
        pwd_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email, is_active",
                (email, pwd_hash),
            )
            row = cur.fetchone()
            conn.commit()
        return {"id": row[0], "email": row[1], "is_active": row[2]}

    def verify_password(self, password: str, password_hash: str) -> bool:
        return check_password_hash(password_hash, password)

    def public_user(self, u: Dict[str, Any]) -> Dict[str, Any]:
        return {"id": u["id"], "email": u["email"], "is_active": u["is_active"]}
