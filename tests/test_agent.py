"""Unit tests for BikeFit Agent ADK configuration, subagents, and callbacks."""

import pytest
from bikefit_agent.agent import root_agent
from bikefit_agent.state import BikeFitState
from bikefit_agent.telemetry import trace_before_tool, trace_after_tool, trace_on_tool_error


def test_root_agent_initialization():
    """Verify root agent metadata and instructions."""
    assert root_agent.name == "bikefit_agent"
    assert "BikeFit AI" in root_agent.instruction
    assert root_agent.state_schema == BikeFitState


def test_root_agent_tools_count():
    """Verify all 8 core tools are registered on root agent."""
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
    ]
    for expected in expected_tools:
        assert expected in tool_names


def test_root_agent_subagents():
    """Verify specialized subagents are configured."""
    subagent_names = [sa.name for sa in root_agent.sub_agents]
    assert "safety_agent" in subagent_names
    assert "comparison_agent" in subagent_names


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
