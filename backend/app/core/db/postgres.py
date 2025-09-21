# backend/app/core/db/postgres.py
import psycopg
from app.core.db.base import DatabaseAdapter

class PostgresAdapter(DatabaseAdapter):
    def __init__(self, host, port, name, user, password):
        self.dsn = f"host={host} port={port} dbname={name} user={user} password={password}"
        self.conn = None
        self.cur = None

    def connect(self):
        if not self.conn:
            self.conn = psycopg.connect(self.dsn, autocommit=False)
            self.cur = self.conn.cursor()

    def close(self):
        if self.cur: self.cur.close()
        if self.conn: self.conn.close()
        self.cur = None; self.conn = None

    def execute(self, sql, params=None): self.cur.execute(sql, params or ())
    def fetchone(self): return self.cur.fetchone()
    def fetchall(self): return self.cur.fetchall()
    def commit(self): self.conn.commit()
    def rollback(self): self.conn.rollback()
