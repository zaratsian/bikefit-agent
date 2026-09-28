"""Bike geometry catalog and search tools.

Loads and queries verified bicycle frame geometry specifications from local JSON.
All tools return strict Pydantic models for validated, type-safe output schemas.
"""

import json
import os
from typing import List, Optional
from pydantic import BaseModel, Field


class BikeSpec(BaseModel):
    """Strict schema for individual bike geometry specifications."""
    brand: str = Field(..., description="Bicycle manufacturer brand")
    model: str = Field(..., description="Bicycle frame model")
    category: str = Field(..., description="Frame category: Race, Endurance, Aero Race, or Gravel")
    year: int = Field(..., description="Model release year")
    size: str = Field(..., description="Frame size label")
    stack_mm: float = Field(..., description="Frame stack in mm")
    reach_mm: float = Field(..., description="Frame reach in mm")
    head_tube_angle_deg: float = Field(..., description="Head tube angle in degrees")
    seat_tube_angle_deg: float = Field(..., description="Seat tube angle in degrees")
    bb_drop_mm: float = Field(..., description="Bottom bracket drop in mm")
    wheelbase_mm: float = Field(..., description="Wheelbase in mm")
    tire_clearance_mm: float = Field(..., description="Max tire clearance in mm")
    description: str = Field(..., description="Model overview and intended use")


class BikeSizeOption(BaseModel):
    """Summary of geometry for a specific size option."""
    size: str = Field(..., description="Frame size")
    stack_mm: float = Field(..., description="Frame stack in mm")
    reach_mm: float = Field(..., description="Frame reach in mm")
    str_ratio: float = Field(..., description="Stack-to-reach ratio")
    category: str = Field(..., description="Frame category")


class BikeLookupResult(BaseModel):
    """Strict output schema for bike catalog queries."""
    found: bool = Field(..., description="Whether a matching bike was located")
    error: Optional[str] = Field(default=None, description="Error message if not found")
    bike: Optional[BikeSpec] = Field(default=None, description="Matched bike specification when size is specified")
    stack_to_reach_ratio: Optional[float] = Field(default=None, description="Stack-to-reach ratio")
    fit_summary: Optional[str] = Field(default=None, description="Human-readable geometry summary")
    multiple_sizes_available: bool = Field(default=False, description="True if multiple sizes match without exact size filter")
    brand: Optional[str] = Field(default=None, description="Matched brand name")
    model: Optional[str] = Field(default=None, description="Matched model name")
    available_sizes: List[str] = Field(default_factory=list, description="Available frame sizes for this model")
    sizes_details: List[BikeSizeOption] = Field(default_factory=list, description="Detailed geometry per size option")
    available_models: List[str] = Field(default_factory=list, description="Alternative models in catalog if search missed")


class BikeFrameSummary(BaseModel):
    """Compact summary of a bike frame for side-by-side comparison."""
    name: str = Field(..., description="Brand and model name")
    size: str = Field(..., description="Frame size")
    category: str = Field(..., description="Frame category")
    stack_mm: float = Field(..., description="Frame stack in mm")
    reach_mm: float = Field(..., description="Frame reach in mm")
    hta_deg: float = Field(..., description="Head tube angle in degrees")
    stack_to_reach: float = Field(..., description="Stack-to-reach ratio")


class GeometryDelta(BaseModel):
    """Metric differences between two bike frames."""
    delta_stack_mm: float = Field(..., description="Difference in stack (Bike 2 - Bike 1) in mm")
    delta_reach_mm: float = Field(..., description="Difference in reach (Bike 2 - Bike 1) in mm")
    delta_str_ratio: float = Field(..., description="Difference in STR ratio (Bike 2 - Bike 1)")


class BikeComparisonResult(BaseModel):
    """Strict output schema for side-by-side bike comparison."""
    found: bool = Field(default=True, description="Whether both bikes were successfully resolved")
    error: Optional[str] = Field(default=None, description="Error message if any bike was not found")
    bike_1: Optional[BikeFrameSummary] = Field(default=None, description="First bike summary")
    bike_2: Optional[BikeFrameSummary] = Field(default=None, description="Second bike summary")
    differences: Optional[GeometryDelta] = Field(default=None, description="Delta differences in stack and reach")
    posture_shift: Optional[str] = Field(default=None, description="Biomechanical posture shift assessment")


class BikeSearchItem(BaseModel):
    """Summary item in category search results."""
    brand: str = Field(..., description="Brand")
    model: str = Field(..., description="Model")
    category: str = Field(..., description="Category")
    size: str = Field(..., description="Size")
    stack_mm: float = Field(..., description="Stack in mm")
    reach_mm: float = Field(..., description="Reach in mm")
    str_ratio: float = Field(..., description="Stack-to-reach ratio")


class BikeSearchResult(BaseModel):
    """Strict output schema for bike category search."""
    count: int = Field(..., description="Number of matching bikes found")
    results: List[BikeSearchItem] = Field(default_factory=list, description="List of matching bikes")


class BikeListResult(BaseModel):
    """Strict output schema for full bike catalog listing."""
    total_models: int = Field(..., description="Total unique bike models in catalog")
    models: List[str] = Field(default_factory=list, description="List of available models with category tags")


def _get_catalog_path() -> str:
    """Resolve path to the bundled bikes.json catalog."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    catalog_path = os.path.join(os.path.dirname(current_dir), "data", "bikes.json")
    if not os.path.exists(catalog_path):
        catalog_path = os.path.join(os.getcwd(), "bikefit_agent", "data", "bikes.json")
    return catalog_path


def load_catalog() -> List[dict]:
    """Load the full bike catalog from JSON."""
    path = _get_catalog_path()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("bikes", [])


def lookup_bike(query: str, size: Optional[str] = None) -> BikeLookupResult:
    """Look up geometry specifications for a bike model and optional size.

    Args:
        query: Name of the bike brand and/or model (e.g. 'Tarmac SL8', 'Domane', 'Canyon Ultimate').
        size: Specific frame size (e.g. '54', '56', 'M', 'L').

    Returns:
        BikeLookupResult: Strict Pydantic model containing matched bike details or list of available sizes.
    """
    bikes = load_catalog()
    query_lower = query.lower()
    matches = []

    for b in bikes:
        full_name = f"{b['brand']} {b['model']}".lower()
        if query_lower in full_name or all(part in full_name for part in query_lower.split()):
            matches.append(b)

    if not matches:
        return BikeLookupResult(
            found=False,
            error=f"No bikes found matching query '{query}'.",
            available_models=sorted(list(set(f"{b['brand']} {b['model']}" for b in bikes)))
        )

    # If size is specified, filter by size
    if size:
        size_str = str(size).strip().upper()
        exact_matches = [m for m in matches if str(m["size"]).strip().upper() == size_str]
        if exact_matches:
            b = exact_matches[0]
            str_ratio = round(b["stack_mm"] / b["reach_mm"], 2)
            bike_obj = BikeSpec(**b)
            return BikeLookupResult(
                found=True,
                bike=bike_obj,
                stack_to_reach_ratio=str_ratio,
                fit_summary=f"{b['brand']} {b['model']} Size {b['size']} (Stack: {b['stack_mm']}mm, Reach: {b['reach_mm']}mm, STR: {str_ratio})"
            )

    # If size not specified or not matched, return list of available sizes
    sizes_details = [
        BikeSizeOption(
            size=m["size"],
            stack_mm=m["stack_mm"],
            reach_mm=m["reach_mm"],
            str_ratio=round(m["stack_mm"] / m["reach_mm"], 2),
            category=m["category"]
        )
        for m in matches
    ]

    return BikeLookupResult(
        found=True,
        multiple_sizes_available=True,
        brand=matches[0]["brand"],
        model=matches[0]["model"],
        available_sizes=[m["size"] for m in matches],
        sizes_details=sizes_details
    )


def compare_two_bikes(
    bike1_query: str,
    size1: str,
    bike2_query: str,
    size2: str
) -> BikeComparisonResult:
    """Compare geometry specifications and stack-to-reach posture between two specific bike frames and sizes.

    Args:
        bike1_query: Brand/model for first bike (e.g. 'Trek Domane').
        size1: Frame size for first bike (e.g. '56').
        bike2_query: Brand/model for second bike (e.g. 'Specialized Tarmac SL8').
        size2: Frame size for second bike (e.g. '56').

    Returns:
        BikeComparisonResult: Strict Pydantic model with side-by-side comparison, differences, and posture shift analysis.
    """
    b1_res = lookup_bike(bike1_query, size1)
    b2_res = lookup_bike(bike2_query, size2)

    if not b1_res.found or not b1_res.bike:
        return BikeComparisonResult(found=False, error=f"Could not find first bike: {bike1_query} size {size1}")
    if not b2_res.found or not b2_res.bike:
        return BikeComparisonResult(found=False, error=f"Could not find second bike: {bike2_query} size {size2}")

    bike1 = b1_res.bike
    bike2 = b2_res.bike

    delta_stack = round(bike2.stack_mm - bike1.stack_mm, 1)
    delta_reach = round(bike2.reach_mm - bike1.reach_mm, 1)

    str1 = round(bike1.stack_mm / bike1.reach_mm, 2)
    str2 = round(bike2.stack_mm / bike2.reach_mm, 2)

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

    return BikeComparisonResult(
        found=True,
        bike_1=BikeFrameSummary(
            name=f"{bike1.brand} {bike1.model}",
            size=bike1.size,
            category=bike1.category,
            stack_mm=bike1.stack_mm,
            reach_mm=bike1.reach_mm,
            hta_deg=bike1.head_tube_angle_deg,
            stack_to_reach=str1,
        ),
        bike_2=BikeFrameSummary(
            name=f"{bike2.brand} {bike2.model}",
            size=bike2.size,
            category=bike2.category,
            stack_mm=bike2.stack_mm,
            reach_mm=bike2.reach_mm,
            hta_deg=bike2.head_tube_angle_deg,
            stack_to_reach=str2,
        ),
        differences=GeometryDelta(
            delta_stack_mm=delta_stack,
            delta_reach_mm=delta_reach,
            delta_str_ratio=round(str2 - str1, 2)
        ),
        posture_shift=posture_shift
    )


def search_bikes_by_category(category: str, size: Optional[str] = None) -> BikeSearchResult:
    """Search for bikes in the catalog by category (e.g. 'Race', 'Endurance', 'Aero Race', 'Gravel').

    Args:
        category: Bike category ('Race', 'Endurance', 'Aero Race', 'Gravel').
        size: Optional size to filter (e.g. '54', '56', 'M').

    Returns:
        BikeSearchResult: Strict Pydantic model with list of matching bikes and key geometry numbers.
    """
    bikes = load_catalog()
    cat_lower = category.lower()
    results = []

    for b in bikes:
        if cat_lower in b["category"].lower():
            if size is None or str(b["size"]).strip().upper() == str(size).strip().upper():
                results.append(BikeSearchItem(
                    brand=b["brand"],
                    model=b["model"],
                    category=b["category"],
                    size=b["size"],
                    stack_mm=b["stack_mm"],
                    reach_mm=b["reach_mm"],
                    str_ratio=round(b["stack_mm"] / b["reach_mm"], 2)
                ))

    return BikeSearchResult(count=len(results), results=results)


def list_all_bikes() -> BikeListResult:
    """List all available bike models in the catalog.

    Returns:
        BikeListResult: Strict Pydantic model with total count and unique models in catalog.
    """
    bikes = load_catalog()
    unique = sorted(list(set(f"{b['brand']} {b['model']} ({b['category']})" for b in bikes)))
    return BikeListResult(total_models=len(unique), models=unique)
