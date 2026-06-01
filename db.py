import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "predict.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate_users(conn: sqlite3.Connection) -> None:
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


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
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
        )
        _migrate_users(conn)

        count = conn.execute("SELECT COUNT(*) FROM markets").fetchone()[0]
        if count == 0:
            seed_markets(conn)


def seed_markets(conn: sqlite3.Connection) -> None:
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
