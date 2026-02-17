"""
Database manager for AI settings
SQLite database to store API keys and GPM configuration
"""

import sqlite3
from typing import Dict, Optional
from datetime import datetime
import os
from pathlib import Path


class AISettingsDatabase:
    """Manages AI settings data in SQLite database"""
    
    def __init__(self, db_path: str = "ai_settings.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        # Ensure database directory exists
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dicts
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # AI Settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL UNIQUE,
                api_key TEXT,
                base_url TEXT,
                model TEXT,
                gpm_token TEXT,
                gpm_profile_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                last_tested TIMESTAMP,
                test_status TEXT,
                test_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default rows for each provider
        cursor.execute("""
            INSERT OR IGNORE INTO ai_settings (provider) VALUES 
                ('openai_api'),
                ('gemini_api'),
                ('custom_api')
        """)
        
        # App settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL UNIQUE,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Active content provider (replaces default_provider)
        cursor.execute("""
            INSERT OR IGNORE INTO app_settings (key, value) VALUES ('active_provider', '')
        """)
        
        # Legacy: keep default_provider for backward compat
        cursor.execute("""
            INSERT OR IGNORE INTO app_settings (key, value) VALUES ('default_provider', 'gemini_api')
        """)
        
        self.conn.commit()
    
    def get_setting(self, provider: str) -> Optional[Dict]:
        """
        Get settings for a specific provider
        
        Args:
            provider: Provider name ('gemini_api', 'chatgpt_plus', etc.)
            
        Returns:
            Settings dict or None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ai_settings WHERE provider = ?", (provider,))
        row = cursor.fetchone()
        
        return dict(row) if row else None
    
    def get_all_settings(self) -> Dict[str, Dict]:
        """
        Get all AI settings
        
        Returns:
            Dict mapping provider to settings
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ai_settings")
        rows = cursor.fetchall()
        
        return {row['provider']: dict(row) for row in rows}
    
    def update_setting(
        self,
        provider: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        gpm_token: Optional[str] = None,
        gpm_profile_id: Optional[str] = None,
        test_status: Optional[str] = None,
        test_message: Optional[str] = None
    ) -> bool:
        """
        Update settings for a provider
        
        Args:
            provider: Provider name
            api_key: API key (for OpenAI/Gemini API)
            base_url: Custom base URL (for OpenAI - optional)
            model: Model to use (for OpenAI - optional)
            gpm_token: GPM API token (legacy)
            gpm_profile_id: GPM profile ID (legacy)
            test_status: 'success', 'failed', 'not_tested'
            test_message: Error message if test failed
            
        Returns:
            True if successful
        """
        cursor = self.conn.cursor()
        
        # Build update query based on provided fields
        updates = []
        values = []
        
        if api_key is not None:
            updates.append("api_key = ?")
            values.append(api_key)
        
        if base_url is not None:
            updates.append("base_url = ?")
            values.append(base_url)
        
        if model is not None:
            updates.append("model = ?")
            values.append(model)
        
        if gpm_token is not None:
            updates.append("gpm_token = ?")
            values.append(gpm_token)
        
        if gpm_profile_id is not None:
            updates.append("gpm_profile_id = ?")
            values.append(gpm_profile_id)
        
        if test_status is not None:
            updates.append("test_status = ?")
            values.append(test_status)
            updates.append("last_tested = ?")
            values.append(datetime.now().isoformat())
        
        if test_message is not None:
            updates.append("test_message = ?")
            values.append(test_message)
        
        if not updates:
            return False
        
        # Always update timestamp
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        
        # Add provider to values
        values.append(provider)
        
        query = f"UPDATE ai_settings SET {', '.join(updates)} WHERE provider = ?"
        cursor.execute(query, values)
        self.conn.commit()
        
        return cursor.rowcount > 0
    
    def get_default_provider(self) -> str:
        """Get default AI provider (legacy)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key = 'default_provider'")
        row = cursor.fetchone()
        return row['value'] if row else 'gemini_api'
    
    def set_default_provider(self, provider: str) -> bool:
        """Set default AI provider (legacy)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE app_settings 
            SET value = ?, updated_at = ? 
            WHERE key = 'default_provider'
        """, (provider, datetime.now().isoformat()))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_active_provider(self) -> str:
        """Get the active content provider"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key = 'active_provider'")
        row = cursor.fetchone()
        return row['value'] if row else ''
    
    def set_active_provider(self, provider: str) -> bool:
        """Set the active content provider"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO app_settings (key, value, updated_at)
            VALUES ('active_provider', ?, ?)
        """, (provider, datetime.now().isoformat()))
        self.conn.commit()
        return True
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        """Ensure connection is closed on deletion"""
        self.close()


# Singleton instance
_settings_db_instance = None

def get_settings_db() -> AISettingsDatabase:
    """Get or create settings database instance"""
    global _settings_db_instance
    if _settings_db_instance is None:
        db_path = os.path.join(os.path.dirname(__file__), "..", "ai_settings.db")
        _settings_db_instance = AISettingsDatabase(db_path)
    return _settings_db_instance
