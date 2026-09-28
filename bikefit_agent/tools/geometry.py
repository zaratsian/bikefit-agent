"""Bike fit geometry and cockpit coordinate trigonometry tools.

Calculates handlebar positions, solves stem/spacer configurations to replicate
fit coordinates across frames, and audits structural safety and handling.
"""

import math
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CockpitCoordinates(BaseModel):
    """Cockpit coordinate position relative to bottom bracket (0,0)."""
    x_bar_mm: float = Field(..., description="Handlebar X position (horizontal reach from BB in mm)")
    y_bar_mm: float = Field(..., description="Handlebar Y position (vertical stack from BB in mm)")
    stack_to_reach_ratio: float = Field(..., description="Frame stack-to-reach ratio")
    fit_category: str = Field(..., description="Race, Performance, or Endurance classification")
    effective_stem_angle_horizontal_deg: float = Field(..., description="Stem angle relative to horizontal")


class MatchSolution(BaseModel):
    """Stem and spacer solution to replicate a cockpit position."""
    stem_length_mm: int = Field(..., description="Recommended stem length in mm")
    stem_angle_deg: int = Field(..., description="Recommended stem angle in degrees (e.g. -6, +6, -17)")
    spacer_height_mm: float = Field(..., description="Recommended headset spacer stack in mm")
    delta_x_mm: float = Field(..., description="Horizontal error difference in mm")
    delta_y_mm: float = Field(..., description="Vertical error difference in mm")
    total_error_mm: float = Field(..., description="Euclidean distance error in mm")
    is_safe: bool = Field(..., description="Whether the setup meets safety guidelines")
    safety_notes: List[str] = Field(default_factory=list, description="Warnings or guidance")


def calculate_handlebar_position(
    frame_stack_mm: float,
    frame_reach_mm: float,
    head_tube_angle_deg: float,
    spacer_height_mm: float,
    stem_length_mm: float,
    stem_angle_deg: float = -6.0
) -> Dict[str, Any]:
    """Calculate the precise (X, Y) coordinate position of the handlebar center relative to the Bottom Bracket (0, 0).

    Args:
        frame_stack_mm: Vertical height from BB to top of head tube in mm.
        frame_reach_mm: Horizontal reach from BB to center of top of head tube in mm.
        head_tube_angle_deg: Head tube angle in degrees (typically 71.0 - 74.0).
        spacer_height_mm: Height of headset spacers under the stem in mm (typically 0 - 40mm).
        stem_length_mm: Length of the stem along its center line in mm (typically 80 - 130mm).
        stem_angle_deg: Stem angle relative to perpendicular to steerer tube in degrees (e.g., -6, -17, +6).

    Returns:
        A dictionary containing the X and Y coordinates (mm), stack-to-reach ratio, and fit category.
    """
    steerer_rad = math.radians(head_tube_angle_deg)
    
    # Vector along steerer tube for spacers (points backward and upward)
    delta_x_spacer = -spacer_height_mm * math.cos(steerer_rad)
    delta_y_spacer = spacer_height_mm * math.sin(steerer_rad)

    # Angle of the stem relative to the horizontal ground
    # Perpendicular to steerer is (90.0 - HTA) above horizontal
    stem_angle_horizontal = (90.0 - head_tube_angle_deg) + stem_angle_deg
    stem_rad = math.radians(stem_angle_horizontal)

    # Vector along stem length
    delta_x_stem = stem_length_mm * math.cos(stem_rad)
    delta_y_stem = stem_length_mm * math.sin(stem_rad)

    # Total handlebar center coordinates from Bottom Bracket
    x_bar = round(frame_reach_mm + delta_x_spacer + delta_x_stem, 1)
    y_bar = round(frame_stack_mm + delta_y_spacer + delta_y_stem, 1)

    str_ratio = round(frame_stack_mm / frame_reach_mm, 2)
    if str_ratio < 1.45:
        category = "Aggressive Race"
    elif str_ratio <= 1.53:
        category = "Performance All-Round"
    else:
        category = "Comfort Endurance"

    return {
        "x_bar_mm": x_bar,
        "y_bar_mm": y_bar,
        "stack_to_reach_ratio": str_ratio,
        "fit_category": category,
        "effective_stem_angle_horizontal_deg": round(stem_angle_horizontal, 1),
        "delta_spacer_x_mm": round(delta_x_spacer, 1),
        "delta_spacer_y_mm": round(delta_y_spacer, 1),
        "delta_stem_x_mm": round(delta_x_stem, 1),
        "delta_stem_y_mm": round(delta_y_stem, 1),
    }


def solve_cockpit_match(
    current_stack_mm: float,
    current_reach_mm: float,
    current_hta_deg: float,
    current_spacer_mm: float,
    current_stem_len_mm: float,
    current_stem_angle_deg: float,
    target_stack_mm: float,
    target_reach_mm: float,
    target_hta_deg: float,
    max_spacer_mm: float = 40.0
) -> Dict[str, Any]:
    """Find the optimal stem length, stem angle, and spacer stack to match a rider's current handlebar coordinates on a new bike frame.

    Args:
        current_stack_mm: Baseline bike frame stack in mm.
        current_reach_mm: Baseline bike frame reach in mm.
        current_hta_deg: Baseline bike head tube angle in degrees.
        current_spacer_mm: Baseline spacer height in mm.
        current_stem_len_mm: Baseline stem length in mm.
        current_stem_angle_deg: Baseline stem angle in degrees (e.g. -6.0).
        target_stack_mm: Target new frame stack in mm.
        target_reach_mm: Target new frame reach in mm.
        target_hta_deg: Target new frame head tube angle in degrees.
        max_spacer_mm: Maximum allowable spacer height in mm (safety ceiling, default 40mm).

    Returns:
        Best configuration dictionary with recommended stem, spacers, delta error, and safety evaluation.
    """
    # 1. Compute target coordinate from baseline setup
    baseline = calculate_handlebar_position(
        current_stack_mm,
        current_reach_mm,
        current_hta_deg,
        current_spacer_mm,
        current_stem_len_mm,
        current_stem_angle_deg
    )
    target_x = baseline["x_bar_mm"]
    target_y = baseline["y_bar_mm"]

    # 2. Search space of realistic commercial components
    candidate_stems = [70, 80, 90, 100, 110, 120, 130, 140]
    candidate_angles = [-17.0, -10.0, -6.0, 0.0, 6.0, 10.0, 17.0]
    # Spacers from 0mm to max_spacer_mm in 2.5mm steps
    spacer_steps = int(max_spacer_mm / 2.5) + 1
    candidate_spacers = [round(i * 2.5, 1) for i in range(spacer_steps)]

    best_solution = None
    min_error = float("inf")

    for stem_len in candidate_stems:
        for stem_ang in candidate_angles:
            for spacer in candidate_spacers:
                candidate = calculate_handlebar_position(
                    target_stack_mm,
                    target_reach_mm,
                    target_hta_deg,
                    spacer,
                    stem_len,
                    stem_ang
                )
                dx = candidate["x_bar_mm"] - target_x
                dy = candidate["y_bar_mm"] - target_y
                error = math.sqrt(dx * dx + dy * dy)

                if error < min_error:
                    min_error = error
                    best_solution = {
                        "stem_length_mm": stem_len,
                        "stem_angle_deg": stem_ang,
                        "spacer_height_mm": spacer,
                        "achieved_x_bar_mm": candidate["x_bar_mm"],
                        "achieved_y_bar_mm": candidate["y_bar_mm"],
                        "target_x_bar_mm": target_x,
                        "target_y_bar_mm": target_y,
                        "delta_x_mm": round(dx, 1),
                        "delta_y_mm": round(dy, 1),
                        "total_error_mm": round(error, 1),
                    }

    # 3. Assess safety and ergonomics
    safety_notes = []
    is_safe = True

    if best_solution["spacer_height_mm"] > 35.0:
        safety_notes.append("High spacer stack (>35mm) near manufacturer limit for carbon steerer tubes.")
    if best_solution["spacer_height_mm"] > 40.0:
        is_safe = False
        safety_notes.append("CRITICAL: Exceeds standard 40mm carbon steerer tube safety maximum.")

    if best_solution["stem_length_mm"] < 90:
        safety_notes.append("Short stem (<90mm) may lead to nervous or twitchy front-end handling.")
    elif best_solution["stem_length_mm"] > 120:
        safety_notes.append("Long stem (>120mm) provides slow, stable steering but increases forward weight bias.")

    if best_solution["stem_angle_deg"] > 0:
        safety_notes.append("Flipped positive stem (+6° or +17°) required to achieve necessary handlebar height.")

    if best_solution["total_error_mm"] > 5.0:
        safety_notes.append(f"Position cannot be perfectly replicated (minimum discrepancy {best_solution['total_error_mm']}mm).")

    best_solution["is_safe"] = is_safe
    best_solution["safety_notes"] = safety_notes
    best_solution["baseline_fit_category"] = baseline["fit_category"]
    best_solution["target_frame_str_ratio"] = round(target_stack_mm / target_reach_mm, 2)

    return best_solution


def calculate_rider_fit_ranges(
    height_cm: float,
    inseam_cm: float,
    flexibility: str = "moderate"
) -> Dict[str, Any]:
    """Calculate recommended starting bike fit parameters based on anthropometric measurements.

    Args:
        height_cm: Rider standing height in centimeters.
        inseam_cm: Rider cycling inseam (crotch to floor barefoot) in centimeters.
        flexibility: Rider spine and hamstring flexibility ('low', 'moderate', 'high').

    Returns:
        Dictionary with recommended saddle height, saddle setback, target stack/reach, and frame size.
    """
    # LeMond formula for saddle height from BB center to top of saddle
    saddle_height_mm = round(inseam_cm * 0.883 * 10, 1)

    # Estimated saddle setback from BB (KOPS baseline)
    saddle_setback_mm = round(inseam_cm * 0.08 * 10, 1)

    # Frame sizing estimation based on inseam and height
    est_road_size = round((inseam_cm * 0.665), 0)

    flex = flexibility.lower()
    if "high" in flex or "flexible" in flex:
        target_str = 1.42
        recommended_category = "Race / Aero"
        notes = "Able to sustain aerodynamic low-torso angles with minimal back fatigue."
    elif "low" in flex or "stiff" in flex:
        target_str = 1.58
        recommended_category = "Endurance / Upright"
        notes = "Upright posture recommended to avoid lower back strain and neck compression."
    else:
        target_str = 1.50
        recommended_category = "Performance All-Round"
        notes = "Balanced posture balancing aerodynamic efficiency and all-day endurance comfort."

    return {
        "height_cm": height_cm,
        "inseam_cm": inseam_cm,
        "recommended_saddle_height_mm": saddle_height_mm,
        "recommended_saddle_setback_mm": saddle_setback_mm,
        "estimated_road_frame_size_cm": int(est_road_size),
        "target_stack_to_reach_ratio": target_str,
        "recommended_category": recommended_category,
        "ergonomic_notes": notes
    }


def evaluate_bike_safety_and_handling(
    spacer_height_mm: float,
    stem_length_mm: float,
    stem_angle_deg: float,
    is_carbon_steerer: bool = True
) -> Dict[str, Any]:
    """Audit the structural safety and steering dynamics of a proposed cockpit setup.

    Args:
        spacer_height_mm: Total spacer height under the stem in mm.
        stem_length_mm: Stem length in mm.
        stem_angle_deg: Stem angle in degrees.
        is_carbon_steerer: True if fork steerer tube is carbon fiber (standard on modern bikes).

    Returns:
        Safety compliance dictionary with risk level, steering responsiveness rating, and recommendations.
    """
    warnings = []
    risk_level = "LOW"

    # Carbon steerer safety
    if is_carbon_steerer:
        if spacer_height_mm > 40.0:
            risk_level = "CRITICAL"
            warnings.append("CRITICAL: Exceeds 40mm carbon steerer limit. Extreme risk of steerer tube cracking under hard braking.")
        elif spacer_height_mm > 30.0:
            risk_level = "MODERATE"
            warnings.append("WARNING: High spacer stack (>30mm) increases flex under sprint loads.")

    # Steering dynamics
    if stem_length_mm < 80:
        handling = "Twitchy / Hyper-Sensitive"
        warnings.append("Stem under 80mm produces very rapid steering response, requiring constant steering corrections.")
    elif stem_length_mm <= 100:
        handling = "Agile / Neutral"
    elif stem_length_mm <= 120:
        handling = "Stable / Predictable (Standard Pro)"
    else:
        handling = "Sluggish / Slow Turn-In"
        warnings.append("Stem over 120mm creates a long turning arc and shifts excessive rider weight onto front axle.")

    # Inverted / flipped stem
    if stem_angle_deg > 10.0:
        warnings.append("High positive angle (+17°) may significantly alter reach dynamics and visual aesthetics.")

    return {
        "risk_level": risk_level,
        "handling_dynamics": handling,
        "warnings": warnings,
        "is_structurally_compliant": (risk_level != "CRITICAL"),
        "max_recommended_spacers_mm": 40.0 if is_carbon_steerer else 50.0
    }
