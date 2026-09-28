"""Unit tests for persistent database memory, compaction, and async memory routines."""

import asyncio
import os
import tempfile
import pytest
from bikefit_agent.memory.persistence import SessionDatabaseManager
from bikefit_agent.memory.compaction import HistoryCompactor, ContextCacheManager
from bikefit_agent.memory.async_tasks import AsyncMemoryManager


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_sqlite_persistence_state(temp_db):
    """Verify storing and loading session state in external SQLite database."""
    db = SessionDatabaseManager(temp_db)
    session_id = "test_rider_session_101"

    test_state = {
        "rider_height_cm": 182.0,
        "rider_inseam_cm": 86.0,
        "rider_flexibility": "high",
        "current_bike_brand": "Specialized",
        "current_bike_model": "Tarmac SL8",
        "current_bike_size": "56",
        "current_spacer_mm": 15.0,
        "current_stem_len_mm": 100.0,
        "last_solution": {"total_error_mm": 0.5}
    }

    db.save_state(session_id, test_state)
    loaded = db.load_state(session_id)

    assert loaded is not None
    assert loaded["session_id"] == session_id
    assert loaded["rider_profile"]["height_cm"] == 182.0
    assert loaded["current_bike"]["model"] == "Tarmac SL8"
    assert loaded["last_solution"]["total_error_mm"] == 0.5


def test_sqlite_persistence_turn_history(temp_db):
    """Verify appending and retrieving turns from database."""
    db = SessionDatabaseManager(temp_db)
    session_id = "test_history_session"

    db.append_turn(session_id, "user", "What size Trek Domane should I ride?")
    db.append_turn(session_id, "model", "Based on your inseam, a size 56 is recommended.")

    history = db.get_history(session_id)
    assert len(history) == 2
    assert history[0].role == "user"
    assert "Trek Domane" in history[0].content
    assert history[1].role == "model"


def test_history_compactor():
    """Verify history compaction summarizes older turns while keeping recent turns verbatim."""
    compactor = HistoryCompactor(max_verbatim_turns=2)

    turns = [
        {"role": "user", "content": "I ride a Trek Domane 56 with 20mm spacers."},
        {"role": "model", "content": "Got it. Your handlebar coordinates are calculated."},
        {"role": "user", "content": "I am looking at a Specialized Tarmac SL8."},
        {"role": "model", "content": "The Tarmac has a much lower front stack."},
        {"role": "user", "content": "Can I match my coordinates on the Tarmac?"},
    ]

    compacted = compactor.compact_history(turns, {"rider_height_cm": 180.0})
    assert compacted.original_turn_count == 5
    assert compacted.compacted_turn_count == 3
    assert len(compacted.recent_turns) == 2
    assert "Prior conversation" in compacted.summary


def test_context_cache_config():
    """Verify Gemini Context Caching configuration."""
    config = ContextCacheManager.get_cache_configuration(ttl_hours=2)
    assert config.ttl_seconds == 7200
    assert "gemini" in config.model
    assert config.estimated_tokens > 5000


def test_async_memory_manager(temp_db):
    """Verify async background tasks for state saving and compaction."""
    async def _run():
        db = SessionDatabaseManager(temp_db)
        async_mgr = AsyncMemoryManager(db)
        session_id = "async_session_1"

        # Async turn recording
        await async_mgr.async_record_turn(session_id, "user", "Looking for gravel bike")
        await async_mgr.async_record_turn(session_id, "model", "Specialized Diverge STR is available")

        # Async state saving
        state = {"rider_height_cm": 178.0, "current_bike_brand": "Canyon"}
        await async_mgr.async_save_state(session_id, state)

        loaded = db.load_state(session_id)
        assert loaded["rider_profile"]["height_cm"] == 178.0

        # Async compaction
        compacted = await async_mgr.async_compact_session(session_id, state)
        assert compacted.original_turn_count == 2

    asyncio.run(_run())
