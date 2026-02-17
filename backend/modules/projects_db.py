"""
Projects Database Module

Stores and manages saved projects for the Podcast Remake workflow.
Uses SQLite for persistence. Follows the same pattern as style_profiles_db.py.
"""

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
        """Initialize database tables"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    style_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def create_project(self, name: str, style_id: Optional[int] = None) -> int:
        """
        Create a new project.

        Args:
            name: Project name
            style_id: Optional linked style profile ID

        Returns:
            Project ID
        """
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (name, status, style_id, created_at, updated_at)
                VALUES (?, 'draft', ?, ?, ?)
                """,
                (name, style_id, now, now)
            )
            return cursor.lastrowid

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Get all projects, newest first"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific project by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_project(self, project_id: int, updates: Dict[str, Any]) -> bool:
        """Update a project"""
        allowed_fields = {'name', 'status', 'style_id'}
        filtered = {k: v for k, v in updates.items() if k in allowed_fields}

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


# Singleton instance
_db_instance: Optional[ProjectsDB] = None


def get_projects_db() -> ProjectsDB:
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ProjectsDB()
    return _db_instance
