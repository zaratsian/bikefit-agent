"""Interactive local test script for BikeFit Agent.

Usage:
    python run_agent.py
"""

import argparse
from bikefit_agent.tools.geometry import (
    calculate_handlebar_position,
    solve_cockpit_match,
    calculate_rider_fit_ranges,
    evaluate_bike_safety_and_handling,
)
from bikefit_agent.tools.catalog import lookup_bike, compare_two_bikes, list_all_bikes


def run_demo():
    print("=" * 70)
    print("🚴‍♂️ BIKEFIT AGENT - AUTONOMOUS BIKE FIT & COCKPIT SOLVER (Google ADK)")
    print("=" * 70)

    print("\n[1] Listing Available Models in Verified Geometry Catalog:")
    catalog = list_all_bikes()
    for b in catalog.models[:6]:
        print(f"   • {b}")

    print("\n[2] Looking up Baseline Bike (Trek Domane SLR Size 56):")
    domane = lookup_bike("Trek Domane", "56")
    print(f"   {domane.fit_summary}")

    print("\n[3] Computing Current Handlebar (X, Y) Coordinates from Bottom Bracket:")
    print("   Setup: 20mm spacers, 100mm stem at -6°")
    coords = calculate_handlebar_position(
        frame_stack_mm=domane.bike.stack_mm,
        frame_reach_mm=domane.bike.reach_mm,
        head_tube_angle_deg=domane.bike.head_tube_angle_deg,
        spacer_height_mm=20.0,
        stem_length_mm=100.0,
        stem_angle_deg=-6.0
    )
    print(f"   👉 Handlebar Center Reach (X_bar): {coords.x_bar_mm} mm")
    print(f"   👉 Handlebar Center Stack (Y_bar): {coords.y_bar_mm} mm")
    print(f"   👉 Classification: {coords.fit_category} (STR: {coords.stack_to_reach_ratio})")

    print("\n[4] Solving Match for Dream Bike: Specialized Tarmac SL8 Size 56 (Race Frame):")
    tarmac = lookup_bike("Specialized Tarmac SL8", "56")
    sol = solve_cockpit_match(
        current_stack_mm=domane.bike.stack_mm,
        current_reach_mm=domane.bike.reach_mm,
        current_hta_deg=domane.bike.head_tube_angle_deg,
        current_spacer_mm=20.0,
        current_stem_len_mm=100.0,
        current_stem_angle_deg=-6.0,
        target_stack_mm=tarmac.bike.stack_mm,
        target_reach_mm=tarmac.bike.reach_mm,
        target_hta_deg=tarmac.bike.head_tube_angle_deg
    )
    print(f"   🎯 Recommended Stem: {sol.stem_length_mm} mm @ {sol.stem_angle_deg}°")
    print(f"   🎯 Recommended Spacers: {sol.spacer_height_mm} mm")
    print(f"   🎯 Fit Error Discrepancy: {sol.total_error_mm} mm")
    print(f"   🛡️ Safety Compliance: {'PASS' if sol.is_safe else 'FAIL'}")
    for note in sol.safety_notes:
        print(f"      ⚠️  {note}")

    print("\n[5] Side-by-Side Frame Geometry & Posture Shift Analysis:")
    comp = compare_two_bikes("Trek Domane", "56", "Specialized Tarmac SL8", "56")
    print(f"   • Delta Stack: {comp.differences.delta_stack_mm} mm")
    print(f"   • Delta Reach: {comp.differences.delta_reach_mm} mm")
    print(f"   • Posture Verdict: {comp.posture_shift}")

    print("\n" + "=" * 70)
    print("✨ To run with the full Google ADK Web UI / LLM:")
    print("   export GOOGLE_API_KEY='your-key'")
    print("   adk web .")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BikeFit Agent CLI Runner")
    parser.add_argument("--demo", action="store_true", default=True, help="Run demonstration suite")
    args = parser.parse_args()
    run_demo()
