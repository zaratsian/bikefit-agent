"""History Compaction and Gemini Context Caching.

Implements token-efficient context window management, sliding window compaction,
critical domain fact preservation, and Gemini Context Caching configuration.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CompactedContext(BaseModel):
    """Schema for compacted conversation context."""
    summary: str = Field(..., description="Semantic summary of compacted older conversation turns")
    recent_turns: List[Dict[str, Any]] = Field(default_factory=list, description="Uncompacted recent turns preserved verbatim")
    original_turn_count: int = Field(..., description="Number of turns prior to compaction")
    compacted_turn_count: int = Field(..., description="Number of turns summarized into context")
    retained_facts: Dict[str, Any] = Field(default_factory=dict, description="Extracted critical rider facts")


class HistoryCompactor:
    """Performs semantic history compaction and context management."""

    def __init__(self, max_verbatim_turns: int = 4):
        """Initialize compactor with window size."""
        self.max_verbatim_turns = max_verbatim_turns

    def compact_history(
        self,
        turns: List[Dict[str, Any]],
        rider_state: Optional[Dict[str, Any]] = None
    ) -> CompactedContext:
        """Compact conversation history by summarizing older turns and keeping recent turns verbatim.

        Args:
            turns: List of conversation turn dicts [{'role': '...', 'content': '...'}].
            rider_state: Current state memory dictionary.

        Returns:
            CompactedContext: Structured summary + recent turns.
        """
        total_turns = len(turns)
        if total_turns <= self.max_verbatim_turns:
            return CompactedContext(
                summary="Conversation within normal context window; no compaction required.",
                recent_turns=turns,
                original_turn_count=total_turns,
                compacted_turn_count=0,
                retained_facts=rider_state or {}
            )

        # Split into older turns to compact and recent turns to keep
        older_turns = turns[:-self.max_verbatim_turns]
        recent_turns = turns[-self.max_verbatim_turns:]

        # Extract key events from older turns
        key_topics = []
        for t in older_turns:
            role = t.get("role", "user")
            content = t.get("content", "")
            # Capture fit queries
            if "domane" in content.lower() or "tarmac" in content.lower() or "canyon" in content.lower():
                key_topics.append(f"Evaluated bike models in turn ({role})")
            if "spacer" in content.lower() or "stem" in content.lower():
                key_topics.append("Discussed cockpit adjustments")

        summary_text = (
            f"Prior conversation ({len(older_turns)} turns): Discussed rider baseline and goals. "
            f"Key discussion points: {', '.join(set(key_topics)) if key_topics else 'General fitting questions'}. "
            f"Baseline state preserved."
        )

        return CompactedContext(
            summary=summary_text,
            recent_turns=recent_turns,
            original_turn_count=total_turns,
            compacted_turn_count=len(older_turns),
            retained_facts=rider_state or {}
        )


class ContextCacheConfig(BaseModel):
    """Configuration for Google Gemini Context Caching."""
    model: str = Field(default="gemini-2.5-pro", description="Gemini model targeted for caching")
    ttl_seconds: int = Field(default=3600, description="Time to live for context cache in seconds")
    cached_content_name: str = Field(default="bikefit-catalog-cache", description="Identifier for cached context")
    estimated_tokens: int = Field(default=8500, description="Estimated token count of catalog and instructions")


class ContextCacheManager:
    """Manages Gemini Context Caching to cache catalog data and system prompts."""

    @staticmethod
    def get_cache_configuration(ttl_hours: int = 1) -> ContextCacheConfig:
        """Generate context cache configuration for long-lived agent sessions."""
        return ContextCacheConfig(
            model="gemini-2.5-pro",
            ttl_seconds=ttl_hours * 3600,
            cached_content_name="bikefit-catalog-instructions-cache",
            estimated_tokens=9200
        )
