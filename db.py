import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "predict.db"
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()


def uses_postgres() -> bool:
    return bool(DATABASE_URL)


def scalar(row):
    if row is None:
        return None
    try:
        return row[0]
    except (KeyError, IndexError, TypeError):
        return next(iter(row.values()))


def _postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class _PgResult:
    def __init__(self, cursor):
        self._cursor = cursor

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()


class _PgConn:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=()):
        import psycopg2.extras

        sql = sql.replace("?", "%s")
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        return _PgResult(cur)

    def executemany(self, sql: str, params_list):
        sql = sql.replace("?", "%s")
        cur = self._conn.cursor()
        cur.executemany(sql, params_list)
        return _PgResult(cur)

    def executescript(self, script: str):
        statements = [s.strip() for s in script.split(";") if s.strip()]
        for stmt in statements:
            self.execute(stmt)


class _SqlConn:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def execute(self, sql: str, params=()):
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, params_list):
        return self._conn.executemany(sql, params_list)

    def executescript(self, script: str):
        return self._conn.executescript(script)


@contextmanager
def db():
    if uses_postgres():
        import psycopg2

        conn = psycopg2.connect(_postgres_url(DATABASE_URL))
        wrapper = _PgConn(conn)
        try:
            yield wrapper
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        wrapper = _SqlConn(conn)
        try:
            yield wrapper
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _migrate_users_sqlite(conn: _SqlConn) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    migrations = [
        ("email", "ALTER TABLE users ADD COLUMN email TEXT"),
        ("password_hash", "ALTER TABLE users ADD COLUMN password_hash TEXT"),
        ("google_id", "ALTER TABLE users ADD COLUMN google_id TEXT"),
        ("auth_provider", "ALTER TABLE users ADD COLUMN auth_provider TEXT DEFAULT 'local'"),
    ]
    for name, sql in migrations:
        if name not in cols:
            conn.execute(sql)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL"
    )


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT,
    display_name TEXT NOT NULL,
    password_hash TEXT,
    google_id TEXT,
    auth_provider TEXT NOT NULL DEFAULT 'local',
    balance REAL NOT NULL DEFAULT 1000.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS markets (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'General',
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    resolution TEXT,
    yes_pool REAL NOT NULL DEFAULT 100.0,
    no_pool REAL NOT NULL DEFAULT 100.0,
    volume REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('yes', 'no')),
    shares REAL NOT NULL,
    cost REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (market_id) REFERENCES markets(id),
    UNIQUE (user_id, market_id, side)
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    side TEXT NOT NULL,
    shares REAL NOT NULL,
    price REAL NOT NULL,
    amount REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (market_id) REFERENCES markets(id)
);
"""

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT,
    display_name TEXT NOT NULL,
    password_hash TEXT,
    google_id TEXT,
    auth_provider TEXT NOT NULL DEFAULT 'local',
    balance DOUBLE PRECISION NOT NULL DEFAULT 1000.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS markets (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'General',
    end_date TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    resolution TEXT,
    yes_pool DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    no_pool DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    volume DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    market_id TEXT NOT NULL REFERENCES markets(id),
    side TEXT NOT NULL CHECK (side IN ('yes', 'no')),
    shares DOUBLE PRECISION NOT NULL,
    cost DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, market_id, side)
);

CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    market_id TEXT NOT NULL REFERENCES markets(id),
    side TEXT NOT NULL,
    shares DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def init_db() -> None:
    with db() as conn:
        if uses_postgres():
            conn.executescript(POSTGRES_SCHEMA)
        else:
            conn.executescript(SQLITE_SCHEMA)
            _migrate_users_sqlite(conn)

        count = scalar(conn.execute("SELECT COUNT(*) FROM markets").fetchone())
        if count == 0:
            seed_markets(conn)


def seed_markets(conn) -> None:
    samples = [
        (
            "m1",
            "Will Bitcoin exceed $150k by end of 2026?",
            "Resolves YES if BTC spot price on major exchanges exceeds $150,000 USD before Jan 1, 2027 UTC.",
            "Crypto",
            "2026-12-31",
        ),
        (
            "m2",
            "Will SpaceX land humans on Mars before 2030?",
            "Resolves YES if SpaceX or a joint mission successfully lands at least one human on Mars before 2030.",
            "Science",
            "2029-12-31",
        ),
        (
            "m3",
            "Will the US Fed cut rates at least twice in 2026?",
            "Resolves YES if the Federal Reserve announces two or more rate cuts during calendar year 2026.",
            "Economics",
            "2026-12-31",
        ),
        (
            "m4",
            "Will AI pass the Turing test in a public demo in 2026?",
            "Resolves YES if a credible public demonstration convinces a majority of expert judges.",
            "Technology",
            "2026-12-31",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO markets (id, title, description, category, end_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        samples,
    )
