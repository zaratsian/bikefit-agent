"""Unit tests for geometry and cockpit coordinate trigonometry."""

import pytest
from bikefit_agent.tools.geometry import (
    calculate_handlebar_position,
    solve_cockpit_match,
    calculate_rider_fit_ranges,
    evaluate_bike_safety_and_handling,
)


def test_calculate_handlebar_position_basic():
    """Verify standard coordinate calculation for road frame."""
    result = calculate_handlebar_position(
        frame_stack_mm=565.0,
        frame_reach_mm=395.0,
        head_tube_angle_deg=73.5,
        spacer_height_mm=20.0,
        stem_length_mm=100.0,
        stem_angle_deg=-6.0
    )
    assert "x_bar_mm" in result
    assert "y_bar_mm" in result
    # X_bar must be reach - spacer_x + stem_x > reach
    assert result["x_bar_mm"] > 395.0
    # Y_bar must be stack + spacer_y + stem_y > stack
    assert result["y_bar_mm"] > 565.0
    assert result["stack_to_reach_ratio"] == 1.43
    assert result["fit_category"] == "Aggressive Race"


def test_calculate_handlebar_position_horizontal_stem():
    """Verify that a -17 deg stem on a 73 deg head tube is exactly horizontal."""
    result = calculate_handlebar_position(
        frame_stack_mm=550.0,
        frame_reach_mm=385.0,
        head_tube_angle_deg=73.0,
        spacer_height_mm=0.0,
        stem_length_mm=100.0,
        stem_angle_deg=-17.0
    )
    # Stem is horizontal: 90 - 73 - 17 = 0 degrees
    assert result["effective_stem_angle_horizontal_deg"] == 0.0
    # delta_stem_y_mm should be 0.0
    assert result["delta_stem_y_mm"] == 0.0
    # delta_stem_x_mm should be 100.0
    assert result["delta_stem_x_mm"] == 100.0
    assert result["x_bar_mm"] == 485.0
    assert result["y_bar_mm"] == 550.0


def test_solve_cockpit_match_close_match():
    """Verify solver finds a stem/spacer combo within 1.5mm tolerance."""
    # Compare Trek Domane 56 to Specialized Tarmac 56
    solution = solve_cockpit_match(
        current_stack_mm=591.0,
        current_reach_mm=377.0,
        current_hta_deg=71.9,
        current_spacer_mm=20.0,
        current_stem_len_mm=100.0,
        current_stem_angle_deg=-6.0,
        target_stack_mm=565.0,
        target_reach_mm=395.0,
        target_hta_deg=73.5
    )
    assert solution["total_error_mm"] <= 2.0
    assert "stem_length_mm" in solution
    assert "spacer_height_mm" in solution
    assert solution["is_safe"] is True


def test_solve_cockpit_match_safety_warning():
    """Verify safety warnings for extreme spacer heights."""
    # Attempting to match an extremely high endurance position on a tiny frame
    solution = solve_cockpit_match(
        current_stack_mm=620.0,
        current_reach_mm=370.0,
        current_hta_deg=72.0,
        current_spacer_mm=35.0,
        current_stem_len_mm=90.0,
        current_stem_angle_deg=6.0,
        target_stack_mm=510.0,  # very low frame
        target_reach_mm=380.0,
        target_hta_deg=72.5,
        max_spacer_mm=50.0
    )
    # Spacers must exceed 35mm
    assert solution["spacer_height_mm"] >= 35.0
    assert len(solution["safety_notes"]) > 0


def test_calculate_rider_fit_ranges():
    """Verify rider fit estimation formulas."""
    res = calculate_rider_fit_ranges(height_cm=180.0, inseam_cm=84.0, flexibility="high")
    assert res["recommended_saddle_height_mm"] == round(84.0 * 0.883 * 10, 1)
    assert res["target_stack_to_reach_ratio"] == 1.42
    assert "Race" in res["recommended_category"]

    res_low = calculate_rider_fit_ranges(height_cm=180.0, inseam_cm=84.0, flexibility="low")
    assert res_low["target_stack_to_reach_ratio"] == 1.58
    assert "Endurance" in res_low["recommended_category"]


def test_evaluate_bike_safety_and_handling():
    """Verify safety audits for carbon steerers and stem handling."""
    safe = evaluate_bike_safety_and_handling(
        spacer_height_mm=20.0,
        stem_length_mm=100.0,
        stem_angle_deg=-6.0,
        is_carbon_steerer=True
    )
    assert safe["is_structurally_compliant"] is True
    assert safe["risk_level"] == "LOW"
    assert safe["handling_dynamics"] == "Agile / Neutral"

    critical = evaluate_bike_safety_and_handling(
        spacer_height_mm=45.0,  # exceeds 40mm
        stem_length_mm=70.0,   # twitchy
        stem_angle_deg=-6.0,
        is_carbon_steerer=True
    )
    assert critical["is_structurally_compliant"] is False
    assert critical["risk_level"] == "CRITICAL"
    assert "Twitchy" in critical["handling_dynamics"]
