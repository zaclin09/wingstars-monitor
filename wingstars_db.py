"""Wing Stars 獨立 DB — 不跟舊專案共用。

只存「看過哪些 post」，用來判斷是否為新貼文。
"""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "wingstars.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS seen_posts (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            account_id TEXT,
            account_name TEXT,
            content TEXT,
            post_url TEXT,
            created_at TEXT,
            first_seen_at TEXT,
            notified_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_seen_username ON seen_posts(username);
        CREATE INDEX IF NOT EXISTS idx_seen_first_seen ON seen_posts(first_seen_at);
    """)
    conn.commit()
    conn.close()


def is_new_post(post_id: str) -> bool:
    """Check if this post_id has never been recorded."""
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM seen_posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    return row is None


def record_post(post: dict, notified: bool) -> None:
    """Record a post as seen (optionally marking that we also pushed notification)."""
    conn = get_conn()
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT OR IGNORE INTO seen_posts
            (id, username, account_id, account_name, content, post_url,
             created_at, first_seen_at, notified_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post["id"], post["username"],
        post.get("account_id", ""), post.get("account_name", ""),
        (post.get("content") or "")[:2000],
        post.get("post_url", ""),
        post.get("created_at", ""),
        now,
        now if notified else None,
    ))
    conn.commit()
    conn.close()


def count_seen() -> int:
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) FROM seen_posts").fetchone()[0]
    conn.close()
    return n


if __name__ == "__main__":
    init_db()
    print(f"Wing Stars DB initialized at {DB_PATH}")
    print(f"  Current seen posts: {count_seen()}")
