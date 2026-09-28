"""Bike geometry catalog and search tools.

Loads and queries verified bicycle frame geometry specifications from local JSON.
"""

import json
import os
from typing import Dict, Any, List, Optional


def _get_catalog_path() -> str:
    """Resolve path to the bundled bikes.json catalog."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    catalog_path = os.path.join(os.path.dirname(current_dir), "data", "bikes.json")
    if not os.path.exists(catalog_path):
        # Fallback to current working directory
        catalog_path = os.path.join(os.getcwd(), "bikefit_agent", "data", "bikes.json")
    return catalog_path


def load_catalog() -> List[Dict[str, Any]]:
    """Load the full bike catalog from JSON."""
    path = _get_catalog_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("bikes", [])


def lookup_bike(query: str, size: Optional[str] = None) -> Dict[str, Any]:
    """Look up geometry specifications for a bike model and optional size.

    Args:
        query: Name of the bike brand and/or model (e.g. 'Tarmac SL8', 'Domane', 'Canyon Ultimate').
        size: Specific frame size (e.g. '54', '56', 'M', 'L').

    Returns:
        Dictionary containing matched bike details or list of available sizes.
    """
    bikes = load_catalog()
    query_lower = query.lower()
    matches = []

    for b in bikes:
        full_name = f"{b['brand']} {b['model']}".lower()
        if query_lower in full_name or all(part in full_name for part in query_lower.split()):
            matches.append(b)

    if not matches:
        return {
            "found": False,
            "error": f"No bikes found matching query '{query}'.",
            "available_models": list(set(f"{b['brand']} {b['model']}" for b in bikes))
        }

    # If size is specified, filter by size
    if size:
        size_str = str(size).strip().upper()
        exact_matches = [m for m in matches if str(m["size"]).strip().upper() == size_str]
        if exact_matches:
            b = exact_matches[0]
            str_ratio = round(b["stack_mm"] / b["reach_mm"], 2)
            return {
                "found": True,
                "bike": b,
                "stack_to_reach_ratio": str_ratio,
                "fit_summary": f"{b['brand']} {b['model']} Size {b['size']} (Stack: {b['stack_mm']}mm, Reach: {b['reach_mm']}mm, STR: {str_ratio})"
            }

    # If size not specified or not matched, return list of available sizes
    return {
        "found": True,
        "multiple_sizes_available": True,
        "brand": matches[0]["brand"],
        "model": matches[0]["model"],
        "available_sizes": [m["size"] for m in matches],
        "sizes_details": [
            {
                "size": m["size"],
                "stack_mm": m["stack_mm"],
                "reach_mm": m["reach_mm"],
                "str_ratio": round(m["stack_mm"] / m["reach_mm"], 2),
                "category": m["category"]
            }
            for m in matches
        ]
    }


def compare_two_bikes(
    bike1_query: str,
    size1: str,
    bike2_query: str,
    size2: str
) -> Dict[str, Any]:
    """Compare geometry specifications and stack-to-reach posture between two specific bike frames and sizes.

    Args:
        bike1_query: Brand/model for first bike (e.g. 'Trek Domane').
        size1: Frame size for first bike (e.g. '56').
        bike2_query: Brand/model for second bike (e.g. 'Specialized Tarmac SL8').
        size2: Frame size for second bike (e.g. '56').

    Returns:
        Dictionary with side-by-side comparison, differences in stack and reach, and posture shift analysis.
    """
    b1_res = lookup_bike(bike1_query, size1)
    b2_res = lookup_bike(bike2_query, size2)

    if not b1_res.get("found") or not b1_res.get("bike"):
        return {"error": f"Could not find first bike: {bike1_query} size {size1}"}
    if not b2_res.get("found") or not b2_res.get("bike"):
        return {"error": f"Could not find second bike: {bike2_query} size {size2}"}

    bike1 = b1_res["bike"]
    bike2 = b2_res["bike"]

    delta_stack = round(bike2["stack_mm"] - bike1["stack_mm"], 1)
    delta_reach = round(bike2["reach_mm"] - bike1["reach_mm"], 1)

    str1 = round(bike1["stack_mm"] / bike1["reach_mm"], 2)
    str2 = round(bike2["stack_mm"] / bike2["reach_mm"], 2)

    if delta_stack < -15 and delta_reach > 10:
        posture_shift = "Significantly more aggressive and lower posture"
    elif delta_stack > 15 and delta_reach < -10:
        posture_shift = "Significantly more upright and relaxed endurance posture"
    elif abs(delta_stack) <= 10 and abs(delta_reach) <= 10:
        posture_shift = "Very similar geometry; cockpit adjustment will easily compensate"
    elif delta_stack < 0:
        posture_shift = "Lower front end (requires more spacers or positive stem to match)"
    else:
        posture_shift = "Taller front end (requires fewer spacers or negative stem to match)"

    return {
        "bike_1": {
            "name": f"{bike1['brand']} {bike1['model']}",
            "size": bike1["size"],
            "category": bike1["category"],
            "stack_mm": bike1["stack_mm"],
            "reach_mm": bike1["reach_mm"],
            "hta_deg": bike1["head_tube_angle_deg"],
            "stack_to_reach": str1,
        },
        "bike_2": {
            "name": f"{bike2['brand']} {bike2['model']}",
            "size": bike2["size"],
            "category": bike2["category"],
            "stack_mm": bike2["stack_mm"],
            "reach_mm": bike2["reach_mm"],
            "hta_deg": bike2["head_tube_angle_deg"],
            "stack_to_reach": str2,
        },
        "differences": {
            "delta_stack_mm": delta_stack,
            "delta_reach_mm": delta_reach,
            "delta_str_ratio": round(str2 - str1, 2)
        },
        "posture_shift": posture_shift
    }


def search_bikes_by_category(category: str, size: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search for bikes in the catalog by category (e.g. 'Race', 'Endurance', 'Aero Race', 'Gravel').

    Args:
        category: Bike category ('Race', 'Endurance', 'Aero Race', 'Gravel').
        size: Optional size to filter (e.g. '54', '56', 'M').

    Returns:
        List of matching bikes with key geometry numbers.
    """
    bikes = load_catalog()
    cat_lower = category.lower()
    results = []

    for b in bikes:
        if cat_lower in b["category"].lower():
            if size is None or str(b["size"]).strip().upper() == str(size).strip().upper():
                results.append({
                    "brand": b["brand"],
                    "model": b["model"],
                    "category": b["category"],
                    "size": b["size"],
                    "stack_mm": b["stack_mm"],
                    "reach_mm": b["reach_mm"],
                    "str_ratio": round(b["stack_mm"] / b["reach_mm"], 2)
                })
    return results


def list_all_bikes() -> List[str]:
    """List all available bike models in the catalog."""
    bikes = load_catalog()
    unique = sorted(list(set(f"{b['brand']} {b['model']} ({b['category']})" for b in bikes)))
    return unique
