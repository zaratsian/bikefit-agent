"""Strategic Model Routing and Dynamic LLM Dispatcher.

Implements strategic model routing across the agent hierarchy to optimize for
reasoning depth, latency, and cost:
- Coordinator / Root Agent: gemini-2.5-pro (Complex reasoning & synthesis)
- Safety Audit Subagent: gemini-2.5-flash (Low-latency rule verification)
- Comparison Subagent: gemini-2.5-flash-8b (High-throughput tabular analysis)
"""

import os
from enum import Enum
from typing import Optional


class AgentRole(str, Enum):
    """Specialized agent roles in the BikeFit multi-agent hierarchy."""
    COORDINATOR = "coordinator"
    SAFETY_AUDITOR = "safety_auditor"
    COMPARATOR = "comparator"


# Strategic model configuration by agent role
MODEL_ROUTING_CONFIG = {
    AgentRole.COORDINATOR: os.getenv("BIKEFIT_COORDINATOR_MODEL", "gemini-2.5-pro"),
    AgentRole.SAFETY_AUDITOR: os.getenv("BIKEFIT_SAFETY_MODEL", "gemini-2.5-flash"),
    AgentRole.COMPARATOR: os.getenv("BIKEFIT_COMPARATOR_MODEL", "gemini-2.5-flash-8b"),
}


def get_model_for_role(role: AgentRole) -> str:
    """Resolve the optimal model name for a specific agent role in the hierarchy.

    Args:
        role: The AgentRole (COORDINATOR, SAFETY_AUDITOR, COMPARATOR).

    Returns:
        The strategically selected Gemini model identifier.
    """
    return MODEL_ROUTING_CONFIG.get(role, "gemini-2.5-flash")


def route_query_model(user_query: str) -> str:
    """Dynamically route queries based on task complexity.

    Args:
        user_query: The incoming user message.

    Returns:
        Selected model identifier based on prompt characteristics.
    """
    query_lower = user_query.lower()

    # Highly complex multi-variable matching or custom compromise
    if any(k in query_lower for k in ["compromise", "solve", "replicate", "reproduce", "compare multiple"]):
        return MODEL_ROUTING_CONFIG[AgentRole.COORDINATOR]

    # Quick catalog lookups
    if any(k in query_lower for k in ["list", "what sizes", "search category"]):
        return MODEL_ROUTING_CONFIG[AgentRole.COMPARATOR]

    # Default to flash for standard queries
    return MODEL_ROUTING_CONFIG[AgentRole.SAFETY_AUDITOR]
