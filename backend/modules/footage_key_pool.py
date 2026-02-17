"""
Footage API Key Pool Manager
Manages multiple API keys for Pexels and Pixabay with round-robin rotation.
SQLite-backed storage with usage tracking.
"""

import sqlite3
import os
import logging
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FootageKeyPool:
    """Manages a pool of API keys for Pexels and Pixabay with rotation."""

    def __init__(self, db_path: str = "ai_settings.db"):
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._migrate_from_env()

        # Round-robin index per source
        self._rotation_index: Dict[str, int] = {"pexels": 0, "pixabay": 0}

    def _create_tables(self):
        """Create footage_api_keys table if it doesn't exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS footage_api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL CHECK(source IN ('pexels', 'pixabay')),
                api_key TEXT NOT NULL,
                label TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                request_count INTEGER DEFAULT 0,
                last_used_at TIMESTAMP,
                last_tested_at TIMESTAMP,
                test_status TEXT DEFAULT 'untested',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Unique constraint on (source, api_key) to prevent duplicates
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_footage_keys_unique
            ON footage_api_keys(source, api_key)
        """)

        self.conn.commit()

    def _migrate_from_env(self):
        """
        On first run, import existing .env keys into the pool.
        Only imports if the pool for that source is completely empty.
        """
        from dotenv import load_dotenv

        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)

        placeholders = {
            "your_pexels_api_key_here",
            "your_pixabay_api_key_here",
            "",
        }

        for source, env_var in [("pexels", "PEXELS_API_KEY"), ("pixabay", "PIXABAY_API_KEY")]:
            existing = self.get_keys(source)
            if len(existing) > 0:
                continue  # Already has keys, skip migration

            env_key = os.getenv(env_var, "")
            if env_key and env_key not in placeholders:
                self.add_key(source, env_key, label="Default (from .env)")
                logger.info(f"[KeyPool] Migrated {source} key from .env")

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def add_key(self, source: str, api_key: str, label: str = "") -> Optional[int]:
        """
        Add a new API key to the pool.
        Returns the key ID, or None if duplicate.
        """
        if source not in ("pexels", "pixabay"):
            raise ValueError("source must be 'pexels' or 'pixabay'")

        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO footage_api_keys (source, api_key, label)
                   VALUES (?, ?, ?)""",
                (source, api_key.strip(), label.strip()),
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None  # Duplicate key

    def remove_key(self, key_id: int) -> bool:
        """Remove a key by its ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM footage_api_keys WHERE id = ?", (key_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_keys(self, source: str) -> List[Dict]:
        """Get all keys for a given source."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM footage_api_keys WHERE source = ? ORDER BY created_at ASC",
            (source,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_key_by_id(self, key_id: int) -> Optional[Dict]:
        """Get a single key by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM footage_api_keys WHERE id = ?", (key_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def toggle_key(self, key_id: int, is_active: bool) -> bool:
        """Enable or disable a key."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE footage_api_keys SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, key_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def update_test_status(self, key_id: int, status: str) -> bool:
        """Update the test status of a key ('success', 'failed', 'untested')."""
        cursor = self.conn.cursor()
        cursor.execute(
            """UPDATE footage_api_keys
               SET test_status = ?, last_tested_at = ?
               WHERE id = ?""",
            (status, datetime.now().isoformat(), key_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    # ── Rotation ──────────────────────────────────────────────────────────────

    def get_next_key(self, source: str) -> Optional[str]:
        """
        Round-robin: get the next active API key for the given source.
        Returns the api_key string, or None if no active keys.
        Also increments usage counter.
        """
        active_keys = self._get_active_keys(source)
        if not active_keys:
            return None

        idx = self._rotation_index.get(source, 0) % len(active_keys)
        chosen = active_keys[idx]

        # Advance rotation index
        self._rotation_index[source] = (idx + 1) % len(active_keys)

        # Update usage stats
        self._increment_usage(chosen["id"])

        logger.info(
            f"[KeyPool] Rotated {source} -> key #{chosen['id']} "
            f"({chosen.get('label', '')}) [usage: {chosen['request_count'] + 1}]"
        )

        return chosen["api_key"]

    def get_active_key_count(self, source: str) -> int:
        """Return number of active keys for a source."""
        return len(self._get_active_keys(source))

    def _get_active_keys(self, source: str) -> List[Dict]:
        """Get all active keys for a source, ordered by ID for consistent rotation."""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT * FROM footage_api_keys
               WHERE source = ? AND is_active = 1
               ORDER BY id ASC""",
            (source,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def _increment_usage(self, key_id: int):
        """Bump the usage counter and last_used timestamp."""
        cursor = self.conn.cursor()
        cursor.execute(
            """UPDATE footage_api_keys
               SET request_count = request_count + 1,
                   last_used_at = ?
               WHERE id = ?""",
            (datetime.now().isoformat(), key_id),
        )
        self.conn.commit()

    def get_pool_status(self) -> Dict:
        """Get summary of the key pool."""
        result = {}
        for source in ("pexels", "pixabay"):
            all_keys = self.get_keys(source)
            active = [k for k in all_keys if k["is_active"]]
            result[source] = {
                "total_keys": len(all_keys),
                "active_keys": len(active),
                "total_requests": sum(k["request_count"] for k in all_keys),
            }
        return result

    def close(self):
        if self.conn:
            self.conn.close()

    def __del__(self):
        self.close()


# ── Singleton ─────────────────────────────────────────────────────────────────

_key_pool_instance: Optional[FootageKeyPool] = None


def get_key_pool() -> FootageKeyPool:
    """Get or create the key pool singleton."""
    global _key_pool_instance
    if _key_pool_instance is None:
        db_path = os.path.join(os.path.dirname(__file__), "..", "ai_settings.db")
        _key_pool_instance = FootageKeyPool(db_path)
    return _key_pool_instance
