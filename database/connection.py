"""
CappyAutoPost - SQLite Database Connection Manager
"""
import sqlite3
import threading
from contextlib import contextmanager
from typing import Generator
from config.settings import DB_PATH

_local = threading.local()

def get_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Get or create a thread-local SQLite connection.
    Ensures WAL mode and row factory are properly configured.
    """
    target_path = str(db_path or DB_PATH)
    if not hasattr(_local, "connection") or _local.connection is None:
        conn = sqlite3.connect(
            target_path,
            timeout=10.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high-concurrency read/write
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        _local.connection = conn
    return _local.connection

@contextmanager
def get_db(db_path: str = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for safe database transactions."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

def init_db(db_path: str = None) -> None:
    """Initialize database tables and indexes."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Accounts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                uid TEXT UNIQUE,
                cookie_raw TEXT NOT NULL,
                proxy TEXT,
                status TEXT DEFAULT 'Unknown',
                last_checked DATETIME,
                posts_count_today INTEGER DEFAULT 0,
                max_posts_per_day INTEGER DEFAULT 20,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Groups Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                name TEXT,
                category TEXT DEFAULT 'Chung',
                requires_approval BOOLEAN DEFAULT 0,
                allow_anonymous BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'Active',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 3. Posts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content_spintax TEXT NOT NULL,
                image_paths_json TEXT DEFAULT '[]',
                use_anonymous BOOLEAN DEFAULT 0,
                category TEXT DEFAULT 'Chung',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 4. Posting History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posting_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                group_id INTEGER,
                post_id INTEGER,
                status TEXT NOT NULL,
                error_message TEXT,
                post_url TEXT,
                posted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE SET NULL,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE SET NULL
            );
        """)
        
        # 5. App Settings (Key-Value)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_category ON groups(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_posted_at ON posting_history(posted_at DESC);")
