"""External Persistent Database and Session History Management.

Provides SQLite and relational database storage for conversation sessions,
rider state snapshots, and turn-by-turn history across runs.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TurnRecord(BaseModel):
    """Schema for a single persistent conversation turn."""
    turn_id: Optional[int] = None
    session_id: str
    role: str
    content: str
    tool_calls: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SessionDatabaseManager:
    """Manages persistent SQLite / relational database storage for agent sessions."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection and ensure tables exist."""
        if not db_path:
            db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.getenv("BIKEFIT_DB_PATH", os.path.join(db_dir, "bikefit_memory.db"))
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and return a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Session State table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_states (
                    session_id TEXT PRIMARY KEY,
                    rider_profile JSON,
                    current_bike JSON,
                    last_solution JSON,
                    updated_at TEXT
                )
            """)
            # Turn History table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_turns (
                    turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES session_states(session_id)
                )
            """)
            conn.commit()

    def save_state(self, session_id: str, state_dict: Dict[str, Any]) -> None:
        """Persist or update state snapshot for a session."""
        now = datetime.now(timezone.utc).isoformat()
        rider_profile = json.dumps({
            "height_cm": state_dict.get("rider_height_cm"),
            "inseam_cm": state_dict.get("rider_inseam_cm"),
            "flexibility": state_dict.get("rider_flexibility"),
        })
        current_bike = json.dumps({
            "brand": state_dict.get("current_bike_brand"),
            "model": state_dict.get("current_bike_model"),
            "size": state_dict.get("current_bike_size"),
            "spacers": state_dict.get("current_spacer_mm"),
            "stem": state_dict.get("current_stem_len_mm"),
        })
        last_solution = json.dumps(state_dict.get("last_solution") or {})

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO session_states (session_id, rider_profile, current_bike, last_solution, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    rider_profile = excluded.rider_profile,
                    current_bike = excluded.current_bike,
                    last_solution = excluded.last_solution,
                    updated_at = excluded.updated_at
            """, (session_id, rider_profile, current_bike, last_solution, now))
            conn.commit()

    def load_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve persisted state snapshot for a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM session_states WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "session_id": row["session_id"],
                "rider_profile": json.loads(row["rider_profile"]),
                "current_bike": json.loads(row["current_bike"]),
                "last_solution": json.loads(row["last_solution"]),
                "updated_at": row["updated_at"],
            }

    def append_turn(self, session_id: str, role: str, content: str, tool_calls: Optional[Any] = None) -> int:
        """Append a conversation turn to the persistent database history."""
        now = datetime.now(timezone.utc).isoformat()
        tc_str = json.dumps(tool_calls) if tool_calls else None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversation_turns (session_id, role, content, tool_calls, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, role, content, tc_str, now))
            conn.commit()
            return cursor.lastrowid

    def get_history(self, session_id: str, limit: int = 50) -> List[TurnRecord]:
        """Fetch conversation turn history ordered by timestamp."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT turn_id, session_id, role, content, tool_calls, timestamp
                FROM conversation_turns
                WHERE session_id = ?
                ORDER BY turn_id ASC
                LIMIT ?
            """, (session_id, limit))
            rows = cursor.fetchall()
            return [
                TurnRecord(
                    turn_id=row["turn_id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    tool_calls=row["tool_calls"],
                    timestamp=row["timestamp"]
                )
                for row in rows
            ]
