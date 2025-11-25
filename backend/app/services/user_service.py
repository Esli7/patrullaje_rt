# backend/app/services/user_service.py
from typing import Optional, Dict, Any, Tuple, List
import psycopg
from werkzeug.security import generate_password_hash, check_password_hash
from app.config.settings import Settings

# id, email, password_hash, is_active, nombre, nip
Row = Tuple[int, str, str, bool, Optional[str], Optional[str]]

class UserService:
    def __init__(self):
        self.dsn = (
            f"host={Settings.DB_HOST} port={Settings.DB_PORT} "
            f"dbname={Settings.DB_NAME} user={Settings.DB_USER} password={Settings.DB_PASSWORD}"
        )

    # --- esquema ---
    def ensure_schema(self):
        # Mantiene tu tabla users e incorpora roles y user_roles (idempotente)
        sql_users = """
        CREATE TABLE IF NOT EXISTS public.users (
          id BIGSERIAL PRIMARY KEY,
          email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          is_active BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
        sql_roles = """
        CREATE TABLE IF NOT EXISTS public.roles (
          id SMALLSERIAL PRIMARY KEY,
          code TEXT NOT NULL UNIQUE,
          name TEXT NOT NULL
        );
        """
        sql_user_roles = """
        CREATE TABLE IF NOT EXISTS public.user_roles (
          user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
          role_id SMALLINT NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
          PRIMARY KEY (user_id, role_id)
        );
        """
        sql_seed_roles = """
        INSERT INTO public.roles(code, name) VALUES
          ('admin', 'Administrador'),
          ('operador', 'Operador'),
          ('usuario', 'Usuario'),
          ('patrullero', 'Patrullero')
        ON CONFLICT (code) DO NOTHING;
        """

        # Ampliaciones de columnas (idempotentes). Postgres soporta IF NOT EXISTS.
        sql_add_cols = """
        ALTER TABLE public.users
          ADD COLUMN IF NOT EXISTS nombre VARCHAR(150),
          ADD COLUMN IF NOT EXISTS nip    VARCHAR(20);
        -- Índice único condicional para nip (permite NULL)
        CREATE UNIQUE INDEX IF NOT EXISTS ux_users_nip
          ON public.users (nip) WHERE nip IS NOT NULL;
        """

        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql_users)
            cur.execute(sql_roles)
            cur.execute(sql_user_roles)
            cur.execute(sql_seed_roles)
            cur.execute(sql_add_cols)
            conn.commit()

    # --- helpers ---
    def _row_to_dict_full(self, row: Row) -> Dict[str, Any]:
        return {
            "id": row[0],
            "email": row[1],
            "password_hash": row[2],
            "is_active": row[3],
            "nombre": row[4],
            "nip": row[5],
        }

    def _row_to_public(self, row: Row) -> Dict[str, Any]:
        return {
            "id": row[0],
            "email": row[1],
            "is_active": row[3],
            "nombre": row[4],
            "nip": row[5],
        }

    def public_user(self, u: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": u["id"],
            "email": u["email"],
            "is_active": u["is_active"],
            "nombre": u.get("nombre"),
            "nip": u.get("nip"),
        }

    # --- lecturas ---
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        email = (email or "").strip().lower()
        sql = """
        SELECT id, email, password_hash, is_active, nombre, nip
        FROM public.users
        WHERE email=%s
        """
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (email,))
            row = cur.fetchone()
            return self._row_to_dict_full(row) if row else None

    def get_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT id, email, password_hash, is_active, nombre, nip
        FROM public.users
        WHERE id=%s
        """
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
            return self._row_to_dict_full(row) if row else None

    def list_users(self, page: int = 1, size: int = 10) -> Dict[str, Any]:
        page = max(page, 1)
        size = max(min(size, 100), 1)
        offset = (page - 1) * size

        count_sql = "SELECT COUNT(*) FROM public.users"
        list_sql = """
        SELECT id, email, password_hash, is_active, nombre, nip
        FROM public.users
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """

        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(count_sql)
            total = cur.fetchone()[0]
            cur.execute(list_sql, (size, offset))
            rows = cur.fetchall()

        items = [self._row_to_public(r) for r in rows]
        return {"items": items, "page": page, "size": size, "total": total}

    # --- escrituras ---
    def create_user(
        self,
        email: str,
        password: str,
        is_active: bool = True,
        *,
        nombre: Optional[str] = None,
        nip: Optional[str] = None,
    ) -> Dict[str, Any]:
        email = (email or "").strip().lower()
        # normalizar NIP a mayúsculas si viene
        nip = (nip.upper() if isinstance(nip, str) else nip)
        pwd_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
        sql = """
        INSERT INTO public.users (email, password_hash, is_active, nombre, nip)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, email, password_hash, is_active, nombre, nip
        """
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (email, pwd_hash, is_active, nombre, nip))
            row = cur.fetchone()
            conn.commit()
        return self._row_to_public(row)

    def update_user(
        self,
        user_id: int,
        *,
        email: Optional[str] = None,
        password: Optional[str] = None,
        is_active: Optional[bool] = None,
        nombre: Optional[str] = None,
        nip: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        sets, params = [], []
        if email is not None:
            email = email.strip().lower()
            sets.append("email=%s")
            params.append(email)
        if password is not None:
            pwd_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
            sets.append("password_hash=%s")
            params.append(pwd_hash)
        if is_active is not None:
            sets.append("is_active=%s")
            params.append(is_active)
        if nombre is not None:
            sets.append("nombre=%s")
            params.append(nombre)
        if nip is not None:
            # normalizar a mayúsculas
            nip = nip.upper() if isinstance(nip, str) else nip
            sets.append("nip=%s")
            params.append(nip)

        if not sets:
            return self.get_by_id(user_id)

        params.append(user_id)
        sql = f"""
        UPDATE public.users
        SET {', '.join(sets)}, updated_at=NOW()
        WHERE id=%s
        RETURNING id, email, password_hash, is_active, nombre, nip
        """
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            row = cur.fetchone()
            conn.commit()
        return self._row_to_public(row) if row else None

    def delete_user(self, user_id: int) -> bool:
        sql = "DELETE FROM public.users WHERE id=%s"
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            deleted = cur.rowcount
            conn.commit()
        return deleted > 0

    # --- roles (helpers simples) ---
    def list_role_codes(self, user_id: int) -> List[str]:
        sql = """
        SELECT r.code
        FROM public.user_roles ur
        JOIN public.roles r ON r.id = ur.role_id
        WHERE ur.user_id = %s
        ORDER BY r.code
        """
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return [row[0] for row in cur.fetchall()]

    def has_role(self, user_id: int, role_code: str) -> bool:
        sql = """
        SELECT 1
        FROM public.user_roles ur
        JOIN public.roles r ON r.id = ur.role_id
        WHERE ur.user_id = %s AND r.code = %s
        LIMIT 1
        """
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, role_code))
            return cur.fetchone() is not None

    def is_admin(self, user_id: int) -> bool:
        return self.has_role(user_id, "admin")

    def assign_role(self, user_id: int, role_code: str) -> bool:
        # asigna (idempotente) un rol existente a un usuario
        sql_get = "SELECT id FROM public.roles WHERE code=%s"
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql_get, (role_code,))
            r = cur.fetchone()
            if not r:
                raise ValueError(f"rol '{role_code}' no existe")
            role_id = r[0]
            cur.execute(
                "INSERT INTO public.user_roles(user_id, role_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, role_id),
            )
            conn.commit()
            return True

    def revoke_role(self, user_id: int, role_code: str) -> bool:
        # quita un rol al usuario (si lo tiene)
        sql_get = "SELECT id FROM public.roles WHERE code=%s"
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql_get, (role_code,))
            r = cur.fetchone()
            if not r:
                return False
            role_id = r[0]
            cur.execute(
                "DELETE FROM public.user_roles WHERE user_id=%s AND role_id=%s",
                (user_id, role_id),
            )
            deleted = cur.rowcount
            conn.commit()
            return deleted > 0

    # --- utilidades extra para roles / catálogo (compat con endpoints) ---
    def ensure_roles_exist(self, codes: List[str]) -> None:
        if not codes:
            return
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            for c in codes:
                code = (c or "").strip().lower()
                if not code:
                    continue
                name = code.capitalize()
                cur.execute(
                    "INSERT INTO public.roles(code, name) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                    (code, name),
                )
            conn.commit()

    def ensure_role(self, code: str) -> None:
        code = (code or "").strip().lower()
        if not code:
            return
        name = code.capitalize()
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO public.roles(code, name) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                (code, name),
            )
            conn.commit()

    # alias por compat con algunos endpoints
    def create_role_if_not_exists(self, code: str) -> None:
        self.ensure_role(code)

    def list_all_roles(self) -> List[Dict[str, Any]]:
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT id, code, name FROM public.roles ORDER BY code")
            rows = cur.fetchall()
        return [{"id": r[0], "code": r[1], "name": r[2]} for r in rows]

    def list_all_role_codes(self) -> List[str]:
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT code FROM public.roles ORDER BY code")
            return [r[0] for r in cur.fetchall()]

    # --- lecturas con roles (para el frontend) ---
    def list_users_with_roles(
        self,
        page: int = 1,
        size: int = 10,
        q: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lista usuarios agregando roles y ordenando por prioridad de rol:
          admin (0) -> usuario (1) -> patrullero (2) -> otros (99), y luego por email ASC.
        Soporta filtro por email/nombre/nip (insensible a mayúsculas).
        """
        page = max(page, 1)
        size = max(min(size, 100), 1)
        offset = (page - 1) * size

        where = ""
        params: Dict[str, Any] = {"size": size, "off": offset}
        if q:
            where = """
            WHERE LOWER(u.email) LIKE %(q)s
               OR LOWER(COALESCE(u.nombre,'')) LIKE %(q)s
               OR LOWER(COALESCE(u.nip,'')) LIKE %(q)s
            """
            params["q"] = f"%{q.lower()}%"

        count_sql = f"SELECT COUNT(*) FROM public.users u {where}"

        list_sql = f"""
        WITH role_rank AS (
          SELECT
            u.id AS user_id,
            MIN(
              CASE LOWER(r.code)
                WHEN 'admin'      THEN 0
                WHEN 'usuario'    THEN 1
                WHEN 'patrullero' THEN 2
                ELSE 99
              END
            ) AS best_rank
          FROM public.users u
          LEFT JOIN public.user_roles ur ON ur.user_id = u.id
          LEFT JOIN public.roles r       ON r.id       = ur.role_id
          GROUP BY u.id
        )
        SELECT
          u.id,
          u.email,
          u.is_active,
          u.nombre,
          u.nip,
          COALESCE(
            ARRAY_AGG(DISTINCT r.code)
              FILTER (WHERE r.code IS NOT NULL),
            '{{}}'
          ) AS roles,
          COALESCE(rr.best_rank, 99) AS best_rank
        FROM public.users u
        LEFT JOIN public.user_roles ur ON ur.user_id = u.id
        LEFT JOIN public.roles r       ON r.id       = ur.role_id
        LEFT JOIN role_rank rr         ON rr.user_id = u.id
        {where}
        GROUP BY u.id, u.email, u.is_active, u.nombre, u.nip, rr.best_rank
        ORDER BY rr.best_rank ASC, u.email ASC
        LIMIT %(size)s OFFSET %(off)s;
        """

        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(count_sql, params if q else {})
            total = cur.fetchone()[0]
            cur.execute(list_sql, params)
            rows = cur.fetchall()

        items = [
            {
                "id": r[0],
                "email": r[1],
                "is_active": r[2],
                "nombre": r[3],
                "nip": r[4],
                "roles": list(r[5] or []),
            }
            for r in rows
        ]
        return {"items": items, "page": page, "size": size, "total": total}

    def get_user_with_roles(self, user_id: int) -> Optional[Dict[str, Any]]:
        sql = """
        SELECT
          u.id,
          u.email,
          u.is_active,
          u.nombre,
          u.nip,
          COALESCE(
            ARRAY_AGG(r.code ORDER BY r.code)
              FILTER (WHERE r.code IS NOT NULL),
            '{}'
          ) AS roles
        FROM public.users u
        LEFT JOIN public.user_roles ur ON ur.user_id = u.id
        LEFT JOIN public.roles r ON r.id = ur.role_id
        WHERE u.id = %s
        GROUP BY u.id, u.email, u.is_active, u.nombre, u.nip;
        """
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            row = cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "email": row[1],
            "is_active": row[2],
            "nombre": row[3],
            "nip": row[4],
            "roles": list(row[5] or []),
        }

    # --- auth utils ---
    def verify_password(self, password: str, password_hash: str) -> bool:
        return check_password_hash(password_hash, password)

    def email_exists(self, email: str) -> bool:
        email = (email or "").strip().lower()
        sql = "SELECT 1 FROM public.users WHERE email=%s"
        with psycopg.connect(self.dsn) as conn, conn.cursor() as cur:
            cur.execute(sql, (email,))
            return cur.fetchone() is not None
