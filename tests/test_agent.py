"""Unit tests for BikeFit Agent ADK configuration, subagents, and callbacks."""

import json
import logging
import pytest
from bikefit_agent.agent import root_agent
from bikefit_agent.subagents.safety_agent import safety_agent
from bikefit_agent.subagents.comparison_agent import comparison_agent
from bikefit_agent.model_router import get_model_for_role, AgentRole, route_query_model
from bikefit_agent.state import BikeFitState
from bikefit_agent.telemetry import (
    trace_before_tool,
    trace_after_tool,
    trace_on_tool_error,
    StructuredJsonFormatter,
)


def test_root_agent_initialization():
    """Verify root agent metadata and instructions."""
    assert root_agent.name == "bikefit_agent"
    assert "BikeFit AI" in root_agent.instruction
    assert root_agent.state_schema == BikeFitState


def test_strategic_model_routing():
    """Verify model routing assigns gemini-3.8-flash across the agent hierarchy."""
    assert root_agent.model == get_model_for_role(AgentRole.COORDINATOR)
    assert "gemini-3.8-flash" in root_agent.model

    assert safety_agent.model == get_model_for_role(AgentRole.SAFETY_AUDITOR)
    assert "gemini-3.8-flash" in safety_agent.model

    assert comparison_agent.model == get_model_for_role(AgentRole.COMPARATOR)
    assert "gemini-3.8-flash" in comparison_agent.model

    # Dynamic routing
    complex_model = route_query_model("Help me solve an impossible compromise across 3 frames")
    assert "gemini-3.8-flash" in complex_model


def test_root_agent_tools_count():
    """Verify all 9 core tools (including HITL approval) are registered on root agent."""
    tool_names = [t.name if hasattr(t, "name") else t.__name__ for t in root_agent.tools]
    expected_tools = [
        "calculate_handlebar_position",
        "solve_cockpit_match",
        "calculate_rider_fit_ranges",
        "lookup_bike",
        "list_all_bikes",
        "compare_two_bikes",
        "search_bikes_by_category",
        "evaluate_bike_safety_and_handling",
        "request_human_approval",
    ]
    for expected in expected_tools:
        assert expected in tool_names


def test_root_agent_subagents():
    """Verify specialized subagents are configured."""
    subagent_names = [sa.name for sa in root_agent.sub_agents]
    assert "safety_agent" in subagent_names
    assert "comparison_agent" in subagent_names


def test_structured_json_formatter():
    """Verify logger emits valid structured JSON lines with required fields."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="bikefit_agent.test",
        level=logging.INFO,
        pathname="test_agent.py",
        lineno=10,
        msg="Testing structured JSON logging with email rider@test.com",
        args=(),
        exc_info=None
    )
    record.structured_data = {"test_metric": 42, "user_email": "sensitive@test.com"}
    formatted_json = formatter.format(record)

    data = json.loads(formatted_json)
    assert data["severity"] == "INFO"
    assert "rider@test.com" not in data["message"]
    assert "[REDACTED_EMAIL]" in data["message"]
    assert data["data"]["test_metric"] == 42
    assert data["data"]["user_email"] == "[REDACTED_PII]"
    assert "timestamp" in data


def test_telemetry_callbacks():
    """Verify telemetry callbacks execute without throwing exceptions."""
    class MockTool:
        name = "test_tool"

    # Call before_tool
    res_before = trace_before_tool(MockTool(), {"arg1": 123}, context=None)
    assert res_before is None

    # Call after_tool
    res_after = trace_after_tool(MockTool(), {"arg1": 123}, context=None, tool_output={"status": "ok"})
    assert res_after is None

    # Call error callback
    res_err = trace_on_tool_error(MockTool(), {}, context=None, error=ValueError("Mock test error"))
    assert res_err is None


def test_bikefit_state_model():
    """Verify state schema instantiation and validation."""
    state = BikeFitState(
        rider_height_cm=182.0,
        rider_inseam_cm=86.0,
        current_bike_brand="Trek",
        current_bike_model="Domane SLR",
        current_bike_size="56",
        current_spacer_mm=25.0
    )
    assert state.rider_height_cm == 182.0
    assert state.current_bike_brand == "Trek"
    assert state.current_spacer_mm == 25.0
    assert state.rider_flexibility == "moderate"
