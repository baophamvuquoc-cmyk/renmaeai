"""
Projects Database Module

Stores and manages saved projects for the Podcast Remake workflow.
Uses SQLite for persistence. Follows the same pattern as style_profiles_db.py.

The `data` column stores a JSON blob with full workflow state:
  styleA, referenceScripts, topic, targetDuration, channelName, language,
  outline, draftSections, finalScript, remakeMode, remakeScript,
  voiceAnalysis, thumbnailAnalysis, titleAnalysis, descriptionAnalysis,
  syncAnalysis, and any other workflow-specific data.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "projects.db")


class ProjectsDB:
    """Database manager for projects"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

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
        """Initialize database tables and run migrations"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    style_id INTEGER,
                    data TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Migration: add `data` column if missing (existing DBs)
            cursor = conn.execute("PRAGMA table_info(projects)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'data' not in columns:
                conn.execute("ALTER TABLE projects ADD COLUMN data TEXT DEFAULT '{}'")
                print("[ProjectsDB] Migrated: added 'data' column")

    def create_project(
        self,
        name: str,
        style_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Create a new project.

        Args:
            name: Project name
            style_id: Optional linked style profile ID
            data: Optional workflow data dict (stored as JSON)

        Returns:
            Project ID
        """
        now = datetime.now().isoformat()
        data_json = json.dumps(data or {}, ensure_ascii=False)
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (name, status, style_id, data, created_at, updated_at)
                VALUES (?, 'draft', ?, ?, ?, ?)
                """,
                (name, style_id, data_json, now, now)
            )
            return cursor.lastrowid

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Get all projects, newest first"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC"
            ).fetchall()
            return [self._row_to_dict(row) for row in rows]

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific project by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,)
            ).fetchone()
            return self._row_to_dict(row) if row else None

    def update_project(self, project_id: int, updates: Dict[str, Any]) -> bool:
        """Update a project"""
        allowed_fields = {'name', 'status', 'style_id', 'data'}
        filtered = {}
        for k, v in updates.items():
            if k not in allowed_fields:
                continue
            if k == 'data' and isinstance(v, dict):
                filtered[k] = json.dumps(v, ensure_ascii=False)
            else:
                filtered[k] = v

        if not filtered:
            return False

        filtered['updated_at'] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in filtered)
        values = list(filtered.values()) + [project_id]

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE projects SET {set_clause} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0

    def delete_project(self, project_id: int) -> bool:
        """Delete a project"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM projects WHERE id = ?",
                (project_id,)
            )
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a Row to dict, deserializing JSON data"""
        d = dict(row)
        raw = d.get('data')
        if raw and isinstance(raw, str):
            try:
                d['data'] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                d['data'] = {}
        elif raw is None:
            d['data'] = {}
        return d


# Singleton instance
_db_instance: Optional[ProjectsDB] = None


def get_projects_db() -> ProjectsDB:
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ProjectsDB()
    return _db_instance
