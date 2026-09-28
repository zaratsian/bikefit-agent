"""Unit tests for bike catalog and lookup tools."""

import pytest
from bikefit_agent.tools.catalog import (
    load_catalog,
    lookup_bike,
    compare_two_bikes,
    search_bikes_by_category,
    list_all_bikes,
    BikeLookupResult,
    BikeComparisonResult,
    BikeSearchResult,
    BikeListResult,
)


def test_load_catalog():
    """Verify catalog loads and contains verified entries."""
    bikes = load_catalog()
    assert len(bikes) >= 10
    first = bikes[0]
    assert "brand" in first
    assert "model" in first
    assert "stack_mm" in first
    assert "reach_mm" in first


def test_lookup_bike_exact_match():
    """Verify looking up a specific model and size returns strict BikeLookupResult."""
    res = lookup_bike("Tarmac SL8", "56")
    assert isinstance(res, BikeLookupResult)
    assert res.found is True
    assert res.bike is not None
    assert res.bike.brand == "Specialized"
    assert res.bike.size == "56"
    assert res.bike.stack_mm == 565.0
    assert res.bike.reach_mm == 395.0


def test_lookup_bike_multiple_sizes():
    """Verify looking up without size returns available sizes in BikeLookupResult."""
    res = lookup_bike("Canyon Ultimate")
    assert isinstance(res, BikeLookupResult)
    assert res.found is True
    assert res.multiple_sizes_available is True
    assert len(res.available_sizes) >= 3


def test_lookup_bike_not_found():
    """Verify handling of unknown bike queries returns guided models."""
    res = lookup_bike("FakeBrand RocketShip9000")
    assert isinstance(res, BikeLookupResult)
    assert res.found is False
    assert res.error is not None
    assert len(res.available_models) > 0


def test_compare_two_bikes():
    """Verify side-by-side comparison of two bikes returns strict BikeComparisonResult."""
    res = compare_two_bikes("Trek Domane", "56", "Trek Madone", "56")
    assert isinstance(res, BikeComparisonResult)
    assert res.found is True
    assert res.bike_1 is not None
    assert res.bike_2 is not None
    assert res.differences is not None
    assert res.differences.delta_stack_mm < 0  # Madone is lower
    assert res.differences.delta_reach_mm > 0  # Madone is longer
    assert res.posture_shift is not None


def test_search_bikes_by_category():
    """Verify filtering by category returns strict BikeSearchResult."""
    gravel = search_bikes_by_category("Gravel")
    assert isinstance(gravel, BikeSearchResult)
    assert gravel.count >= 1
    for b in gravel.results:
        assert "Gravel" in b.category

    endurance = search_bikes_by_category("Endurance", size="56")
    assert isinstance(endurance, BikeSearchResult)
    assert endurance.count >= 1
    for b in endurance.results:
        assert b.size == "56"


def test_list_all_bikes():
    """Verify list_all_bikes returns strict BikeListResult."""
    catalog = list_all_bikes()
    assert isinstance(catalog, BikeListResult)
    assert catalog.total_models >= 5
    assert any("Specialized" in m for m in catalog.models)
    assert any("Trek" in m for m in catalog.models)
