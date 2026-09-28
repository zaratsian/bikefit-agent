"""Asynchronous Background Memory Management.

Executes non-blocking background tasks for memory persistence, history compaction,
and database synchronization using asyncio routines.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from .persistence import SessionDatabaseManager
from .compaction import HistoryCompactor, CompactedContext

logger = logging.getLogger("bikefit_agent.memory")


class AsyncMemoryManager:
    """Handles asynchronous, non-blocking memory tasks for agent sessions."""

    def __init__(self, db_manager: Optional[SessionDatabaseManager] = None):
        """Initialize with database manager and compactor."""
        self.db = db_manager or SessionDatabaseManager()
        self.compactor = HistoryCompactor(max_verbatim_turns=4)

    async def async_save_state(self, session_id: str, state_dict: Dict[str, Any]) -> None:
        """Asynchronously persist state snapshot to database in a background thread."""
        logger.info(f"🔄 [ASYNC_MEMORY] Scheduling background state save for session '{session_id}'")
        # Run blocking SQLite operation in default executor to prevent blocking async event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.db.save_state, session_id, state_dict)
        logger.info(f"💾 [ASYNC_MEMORY] Completed background state save for session '{session_id}'")

    async def async_record_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[Any] = None
    ) -> int:
        """Asynchronously record a conversation turn without blocking response delivery."""
        loop = asyncio.get_running_loop()
        turn_id = await loop.run_in_executor(
            None,
            self.db.append_turn,
            session_id,
            role,
            content,
            tool_calls
        )
        return turn_id

    async def async_compact_session(
        self,
        session_id: str,
        rider_state: Optional[Dict[str, Any]] = None
    ) -> CompactedContext:
        """Asynchronously load turns and execute history compaction in background."""
        loop = asyncio.get_running_loop()
        history_records = await loop.run_in_executor(None, self.db.get_history, session_id)
        turns = [{"role": r.role, "content": r.content} for r in history_records]

        # Compact history asynchronously
        compacted = await loop.run_in_executor(
            None,
            self.compactor.compact_history,
            turns,
            rider_state
        )
        logger.info(
            f"🧹 [ASYNC_MEMORY] Compacted {compacted.compacted_turn_count} turns in session '{session_id}'"
        )
        return compacted

    def schedule_background_flush(self, session_id: str, state_dict: Dict[str, Any]) -> asyncio.Task:
        """Fire-and-forget helper to schedule a background persistence task."""
        task = asyncio.create_task(self.async_save_state(session_id, state_dict))
        return task
