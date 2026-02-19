"""
Production Store — SQLite persistence for completed queue outputs.

Each production record represents one exported queue result with 19 core fields:
1.  project_name       — Tên project (nhóm productions)
2.  sequence_number    — Số thứ tự (tự tăng theo project)
3.  original_link      — Link YouTube gốc
4.  title              — Tên production
5.  description        — Mô tả video (plaintext)
6.  thumbnail          — Thumbnail prompt (plaintext mô tả ảnh bìa)
7.  keywords           — Search keywords cho footage (plaintext, newline-separated)
8.  script_full        — Kịch bản remake đầy đủ (plaintext)
9.  script_split       — Kịch bản đã split (plaintext CSV)
10. voiceover          — Danh sách voice files (comma-separated filenames)
11. video_footage      — Path file footage
12. video_final        — Path video hoàn chỉnh
13. upload_platform    — Tên nền tảng upload (YouTube, TikTok...)
14. channel_name       — Tên kênh
15. video_status       — Trạng thái video (draft, uploaded, published)
16. prompts_reference  — Prompts ảnh tham chiếu (plaintext, newline-separated)
17. prompts_scene_builder — Prompts scene builder (plaintext, newline-separated)
18. prompts_concept    — Prompts ảnh theo concept (plaintext, newline-separated)
19. prompts_video      — Prompts video (plaintext, newline-separated)

Text fields store content directly (not file paths). File path fields: voiceover, video_footage, video_final.
Follows the same singleton pattern as projects_db.py.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "productions.db")


class ProductionStore:
    """Database manager for productions"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()
        self._migrate_filepaths_to_plaintext()

    def _migrate_filepaths_to_plaintext(self):
        """One-time migration: convert file paths back to plaintext for text fields."""
        TEXT_FIELDS = [
            "description", "script_full", "keywords", "thumbnail",
            "prompts_reference", "prompts_scene_builder", "prompts_concept", "prompts_video",
        ]
        try:
            with self._get_connection() as conn:
                rows = conn.execute("SELECT id, " + ", ".join(TEXT_FIELDS) + " FROM productions").fetchall()
                for row in rows:
                    prod_id = row["id"]
                    updates = {}
                    for field in TEXT_FIELDS:
                        val = row[field] or ""
                        # Detect file paths: contains path separators, is short, and ends with extension
                        if val and ('\\' in val or '/' in val) and len(val) < 500:
                            import os
                            if os.path.isfile(val):
                                try:
                                    with open(val, "r", encoding="utf-8") as f:
                                        content = f.read()
                                    updates[field] = content
                                    print(f"[Migration] Prod {prod_id}.{field}: read {len(content)} chars from {val}")
                                except Exception:
                                    # Binary file (e.g. thumbnail image) — clear the path
                                    updates[field] = ""
                                    print(f"[Migration] Prod {prod_id}.{field}: binary file, cleared")
                            else:
                                # File doesn't exist — clear stale path
                                updates[field] = ""
                    if updates:
                        set_clause = ", ".join(f"{k} = ?" for k in updates)
                        conn.execute(
                            f"UPDATE productions SET {set_clause} WHERE id = ?",
                            list(updates.values()) + [prod_id],
                        )
                if any(True for row in rows for field in TEXT_FIELDS if (row[field] or "") and ('\\' in (row[field] or "") or '/' in (row[field] or ""))):
                    print("[Migration] Filepath→plaintext migration complete")
        except Exception as e:
            print(f"[Migration] Error (non-blocking): {e}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS productions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    -- 18 Core Fields
                    project_name TEXT DEFAULT '',
                    sequence_number INTEGER NOT NULL DEFAULT 0,
                    original_link TEXT DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    description TEXT DEFAULT '',
                    thumbnail TEXT DEFAULT '',
                    keywords TEXT DEFAULT '',
                    script_full TEXT DEFAULT '',
                    script_split TEXT DEFAULT '',
                    voiceover TEXT DEFAULT '',
                    video_footage TEXT DEFAULT '',
                    video_final TEXT DEFAULT '',
                    upload_platform TEXT DEFAULT '',
                    channel_name TEXT DEFAULT '',
                    video_status TEXT DEFAULT 'draft',
                    prompts_reference TEXT DEFAULT '',
                    prompts_scene_builder TEXT DEFAULT '',
                    prompts_concept TEXT DEFAULT '',
                    prompts_video TEXT DEFAULT '',

                    -- Original vs Generated metadata
                    original_title TEXT DEFAULT '',
                    original_description TEXT DEFAULT '',
                    thumbnail_url TEXT DEFAULT '',
                    generated_title TEXT DEFAULT '',
                    generated_description TEXT DEFAULT '',
                    generated_thumbnail_prompt TEXT DEFAULT '',

                    -- Internal / System
                    export_dir TEXT DEFAULT '',
                    preset_name TEXT DEFAULT '',
                    voice_id TEXT DEFAULT '',
                    settings_snapshot TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # Migration: add new columns if upgrading from old schema
            existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(productions)").fetchall()}
            new_cols = {
                "project_name": "TEXT DEFAULT ''",
                "sequence_number": "INTEGER NOT NULL DEFAULT 0",
                "original_link": "TEXT DEFAULT ''",
                "description": "TEXT DEFAULT ''",
                "thumbnail": "TEXT DEFAULT ''",
                "keywords": "TEXT DEFAULT ''",
                "script_full": "TEXT DEFAULT ''",
                "script_split": "TEXT DEFAULT ''",
                "voiceover": "TEXT DEFAULT ''",
                "video_footage": "TEXT DEFAULT ''",
                "video_final": "TEXT DEFAULT ''",
                "upload_platform": "TEXT DEFAULT ''",
                "channel_name": "TEXT DEFAULT ''",
                "video_status": "TEXT DEFAULT 'draft'",
                "prompts_reference": "TEXT DEFAULT ''",
                "prompts_scene_builder": "TEXT DEFAULT ''",
                "prompts_concept": "TEXT DEFAULT ''",
                "prompts_video": "TEXT DEFAULT ''",
                "original_title": "TEXT DEFAULT ''",
                "original_description": "TEXT DEFAULT ''",
                "thumbnail_url": "TEXT DEFAULT ''",
                "generated_title": "TEXT DEFAULT ''",
                "generated_description": "TEXT DEFAULT ''",
                "generated_thumbnail_prompt": "TEXT DEFAULT ''",
            }
            for col_name, col_type in new_cols.items():
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE productions ADD COLUMN {col_name} {col_type}")

    def _next_sequence_number(self, conn, project_name: str) -> int:
        """Get next sequence number for a project (auto-increment per project)"""
        row = conn.execute(
            "SELECT COALESCE(MAX(sequence_number), 0) as max_seq FROM productions WHERE project_name = ?",
            (project_name,),
        ).fetchone()
        return (row["max_seq"] or 0) + 1

    def create_production(
        self,
        title: str = "",
        export_dir: str = "",
        project_name: str = "",
        original_link: str = "",
        description: str = "",
        thumbnail: str = "",
        keywords: str = "",
        script_full: str = "",
        script_split: str = "",
        voiceover: str = "",
        video_footage: str = "",
        video_final: str = "",
        upload_platform: str = "",
        channel_name: str = "",
        video_status: str = "draft",
        prompts_reference: str = "",
        prompts_scene_builder: str = "",
        prompts_concept: str = "",
        prompts_video: str = "",
        preset_name: str = "",
        voice_id: str = "",
        settings_snapshot: Optional[Dict] = None,
        original_title: str = "",
        original_description: str = "",
        thumbnail_url: str = "",
        generated_title: str = "",
        generated_description: str = "",
        generated_thumbnail_prompt: str = "",
    ) -> int:
        """Create a new production record. Returns production ID."""
        now = datetime.now().isoformat()
        snapshot_json = json.dumps(settings_snapshot or {}, ensure_ascii=False)

        with self._get_connection() as conn:
            seq = self._next_sequence_number(conn, project_name)
            cursor = conn.execute(
                """
                INSERT INTO productions (
                    project_name, sequence_number, original_link, title, description, thumbnail, keywords,
                    script_full, script_split, voiceover, video_footage, video_final,
                    upload_platform, channel_name, video_status,
                    prompts_reference, prompts_scene_builder, prompts_concept, prompts_video,
                    original_title, original_description, thumbnail_url,
                    generated_title, generated_description, generated_thumbnail_prompt,
                    export_dir, preset_name, voice_id, settings_snapshot,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_name, seq, original_link, title, description, thumbnail, keywords,
                    script_full, script_split, voiceover, video_footage, video_final,
                    upload_platform, channel_name, video_status,
                    prompts_reference, prompts_scene_builder, prompts_concept, prompts_video,
                    original_title, original_description, thumbnail_url,
                    generated_title, generated_description, generated_thumbnail_prompt,
                    export_dir, preset_name, voice_id, snapshot_json,
                    now, now,
                ),
            )
            return cursor.lastrowid

    def get_all_productions(self, search: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """Get all productions, newest first. Optional search by title."""
        with self._get_connection() as conn:
            if search:
                rows = conn.execute(
                    "SELECT * FROM productions WHERE title LIKE ? OR project_name LIKE ? ORDER BY created_at DESC LIMIT ?",
                    (f"%{search}%", f"%{search}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM productions ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_production(self, production_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific production by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM productions WHERE id = ?", (production_id,)
            ).fetchone()
            return self._row_to_dict(row) if row else None

    def update_production(self, production_id: int, updates: Dict[str, Any]) -> bool:
        """Update a production record"""
        allowed_fields = {
            "project_name", "original_link", "title", "description", "thumbnail", "keywords",
            "script_full", "script_split", "voiceover", "video_footage", "video_final",
            "upload_platform", "channel_name", "video_status",
            "prompts_reference", "prompts_scene_builder", "prompts_concept", "prompts_video",
            "original_title", "original_description", "thumbnail_url",
            "generated_title", "generated_description", "generated_thumbnail_prompt",
            "export_dir", "preset_name", "voice_id",
        }
        filtered = {k: v for k, v in updates.items() if k in allowed_fields}

        if not filtered:
            return False

        filtered["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        values = list(filtered.values()) + [production_id]

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE productions SET {set_clause} WHERE id = ?", values
            )
            return cursor.rowcount > 0

    def delete_production(self, production_id: int) -> Optional[str]:
        """Delete a production record. Returns export_dir for cleanup."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT export_dir FROM productions WHERE id = ?", (production_id,)
            ).fetchone()

            if not row:
                return None

            export_dir = row["export_dir"]
            conn.execute("DELETE FROM productions WHERE id = ?", (production_id,))
            return export_dir

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate stats"""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM productions").fetchone()["c"]
            with_video = conn.execute(
                "SELECT COUNT(*) as c FROM productions WHERE video_final != ''"
            ).fetchone()["c"]

            return {
                "total": total,
                "with_video": with_video,
            }

    def scan_export_dir(self, export_dir: str) -> Dict[str, Any]:
        """Scan an export directory and return file details"""
        dir_path = Path(export_dir)
        if not dir_path.exists():
            return {"exists": False, "files": []}

        files = []
        total_size = 0
        for f in dir_path.iterdir():
            if f.is_file():
                size = f.stat().st_size
                total_size += size
                files.append({
                    "name": f.name,
                    "size_bytes": size,
                    "path": str(f),
                    "extension": f.suffix.lower(),
                })

        return {
            "exists": True,
            "files": sorted(files, key=lambda x: x["name"]),
            "total_size_bytes": total_size,
        }

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a Row to dict with JSON parsing for settings_snapshot"""
        d = dict(row)
        if "settings_snapshot" in d and isinstance(d["settings_snapshot"], str):
            try:
                d["settings_snapshot"] = json.loads(d["settings_snapshot"])
            except (json.JSONDecodeError, TypeError):
                d["settings_snapshot"] = {}
        return d


# Singleton
_store_instance: Optional[ProductionStore] = None


def get_production_store() -> ProductionStore:
    """Get or create store instance"""
    global _store_instance
    if _store_instance is None:
        _store_instance = ProductionStore()
    return _store_instance
