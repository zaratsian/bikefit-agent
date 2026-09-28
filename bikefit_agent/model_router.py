"""Strategic Model Routing and Dynamic LLM Dispatcher.

Implements model routing across the agent hierarchy using Gemini 3.8 Flash
(gemini-3.8-flash) for high-performance reasoning, low latency, and efficient tool calling.
"""

import os
from enum import Enum
from typing import Optional


class AgentRole(str, Enum):
    """Specialized agent roles in the BikeFit multi-agent hierarchy."""
    COORDINATOR = "coordinator"
    SAFETY_AUDITOR = "safety_auditor"
    COMPARATOR = "comparator"


# Model configuration by agent role (standardized on gemini-3.8-flash)
MODEL_ROUTING_CONFIG = {
    AgentRole.COORDINATOR: os.getenv("BIKEFIT_COORDINATOR_MODEL", "gemini-3.8-flash"),
    AgentRole.SAFETY_AUDITOR: os.getenv("BIKEFIT_SAFETY_MODEL", "gemini-3.8-flash"),
    AgentRole.COMPARATOR: os.getenv("BIKEFIT_COMPARATOR_MODEL", "gemini-3.8-flash"),
}


def get_model_for_role(role: AgentRole) -> str:
    """Resolve the optimal model name for a specific agent role in the hierarchy.

    Args:
        role: The AgentRole (COORDINATOR, SAFETY_AUDITOR, COMPARATOR).

    Returns:
        The selected Gemini 3.8 Flash model identifier.
    """
    return MODEL_ROUTING_CONFIG.get(role, "gemini-3.8-flash")


def route_query_model(user_query: str) -> str:
    """Dynamically route queries based on task complexity.

    Args:
        user_query: The incoming user message.

    Returns:
        Selected model identifier based on prompt characteristics.
    """
    query_lower = user_query.lower()

    if any(k in query_lower for k in ["compromise", "solve", "replicate", "reproduce", "compare multiple"]):
        return MODEL_ROUTING_CONFIG[AgentRole.COORDINATOR]

    if any(k in query_lower for k in ["list", "what sizes", "search category"]):
        return MODEL_ROUTING_CONFIG[AgentRole.COMPARATOR]

    return MODEL_ROUTING_CONFIG[AgentRole.SAFETY_AUDITOR]
