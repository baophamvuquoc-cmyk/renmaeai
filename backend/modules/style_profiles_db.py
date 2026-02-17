"""
Style Profiles Database Module

Stores and manages saved style profiles for reuse across script generation sessions.
Uses SQLite for persistence.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "style_profiles.db")


class StyleProfilesDB:
    """Database manager for style profiles"""
    
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
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS style_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    tone TEXT,
                    vocabulary_level TEXT,
                    sentence_structure TEXT,
                    pacing TEXT,
                    target_audience TEXT,
                    key_phrases TEXT,
                    transition_style TEXT,
                    hook_style TEXT,
                    emotional_elements TEXT,
                    raw_profile_json TEXT,
                    source_scripts_count INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    is_favorite INTEGER DEFAULT 0,
                    use_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()
    
    def save_profile(
        self,
        name: str,
        profile_data: Dict[str, Any],
        description: str = "",
        source_scripts_count: int = 1
    ) -> int:
        """
        Save a new style profile
        
        Args:
            name: Profile name
            profile_data: StyleProfile dictionary
            description: Optional description
            source_scripts_count: Number of scripts used to create this profile
            
        Returns:
            Profile ID
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Extract key fields from profile
            key_phrases = profile_data.get('key_phrases', [])
            if isinstance(key_phrases, list):
                key_phrases = json.dumps(key_phrases, ensure_ascii=False)
            
            emotional_elements = profile_data.get('emotional_elements', [])
            if isinstance(emotional_elements, list):
                emotional_elements = json.dumps(emotional_elements, ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO style_profiles (
                    name, description, tone, vocabulary_level, sentence_structure,
                    pacing, target_audience, key_phrases, transition_style,
                    hook_style, emotional_elements, raw_profile_json,
                    source_scripts_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name,
                description,
                profile_data.get('tone', 'neutral'),
                profile_data.get('vocabulary_level', 'intermediate'),
                profile_data.get('sentence_structure', 'mixed'),
                profile_data.get('pacing', 'moderate'),
                profile_data.get('target_audience', 'general'),
                key_phrases,
                profile_data.get('transition_style', ''),
                profile_data.get('hook_style', ''),
                emotional_elements,
                json.dumps(profile_data, ensure_ascii=False),
                source_scripts_count,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Get all saved style profiles"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM style_profiles
                ORDER BY is_favorite DESC, use_count DESC, created_at DESC
            """)
            
            profiles = []
            for row in cursor.fetchall():
                profile = dict(row)
                # Parse JSON fields
                if profile.get('key_phrases'):
                    try:
                        profile['key_phrases'] = json.loads(profile['key_phrases'])
                    except:
                        profile['key_phrases'] = []
                if profile.get('emotional_elements'):
                    try:
                        profile['emotional_elements'] = json.loads(profile['emotional_elements'])
                    except:
                        profile['emotional_elements'] = []
                if profile.get('raw_profile_json'):
                    try:
                        profile['raw_profile'] = json.loads(profile['raw_profile_json'])
                    except:
                        profile['raw_profile'] = {}
                profiles.append(profile)
            
            return profiles
    
    def get_profile(self, profile_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific profile by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM style_profiles WHERE id = ?", (profile_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            profile = dict(row)
            # Parse JSON fields
            if profile.get('key_phrases'):
                try:
                    profile['key_phrases'] = json.loads(profile['key_phrases'])
                except:
                    profile['key_phrases'] = []
            if profile.get('raw_profile_json'):
                try:
                    profile['raw_profile'] = json.loads(profile['raw_profile_json'])
                except:
                    profile['raw_profile'] = {}
            
            return profile
    
    def update_profile(self, profile_id: int, updates: Dict[str, Any]) -> bool:
        """Update a profile"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            allowed_fields = ['name', 'description', 'is_favorite']
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key in allowed_fields:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return False
            
            set_clauses.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(profile_id)
            
            cursor.execute(f"""
                UPDATE style_profiles
                SET {', '.join(set_clauses)}
                WHERE id = ?
            """, values)
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_profile(self, profile_id: int) -> bool:
        """Delete a profile"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM style_profiles WHERE id = ?", (profile_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def increment_use_count(self, profile_id: int) -> None:
        """Increment the use count for a profile"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE style_profiles
                SET use_count = use_count + 1, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), profile_id))
            conn.commit()
    
    def toggle_favorite(self, profile_id: int) -> bool:
        """Toggle favorite status"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE style_profiles
                SET is_favorite = CASE WHEN is_favorite = 1 THEN 0 ELSE 1 END,
                    updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), profile_id))
            conn.commit()
            return cursor.rowcount > 0


# Singleton instance
_db_instance: Optional[StyleProfilesDB] = None


def get_style_profiles_db() -> StyleProfilesDB:
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = StyleProfilesDB()
    return _db_instance
