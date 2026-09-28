"""Unit tests for bike catalog and lookup tools."""

import pytest
from bikefit_agent.tools.catalog import (
    load_catalog,
    lookup_bike,
    compare_two_bikes,
    search_bikes_by_category,
    list_all_bikes,
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
    """Verify looking up a specific model and size."""
    res = lookup_bike("Tarmac SL8", "56")
    assert res["found"] is True
    assert res["bike"]["brand"] == "Specialized"
    assert res["bike"]["size"] == "56"
    assert res["bike"]["stack_mm"] == 565.0
    assert res["bike"]["reach_mm"] == 395.0


def test_lookup_bike_multiple_sizes():
    """Verify looking up without size returns available sizes."""
    res = lookup_bike("Canyon Ultimate")
    assert res["found"] is True
    assert res["multiple_sizes_available"] is True
    assert len(res["available_sizes"]) >= 3


def test_lookup_bike_not_found():
    """Verify handling of unknown bike queries."""
    res = lookup_bike("FakeBrand RocketShip9000")
    assert res["found"] is False
    assert "error" in res
    assert len(res["available_models"]) > 0


def test_compare_two_bikes():
    """Verify side-by-side comparison of two bikes."""
    res = compare_two_bikes("Trek Domane", "56", "Trek Madone", "56")
    assert "bike_1" in res
    assert "bike_2" in res
    assert "differences" in res
    assert res["differences"]["delta_stack_mm"] < 0  # Madone is lower
    assert res["differences"]["delta_reach_mm"] > 0  # Madone is longer
    assert "posture_shift" in res


def test_search_bikes_by_category():
    """Verify filtering by category."""
    gravel = search_bikes_by_category("Gravel")
    assert len(gravel) >= 1
    for b in gravel:
        assert "Gravel" in b["category"]

    endurance = search_bikes_by_category("Endurance", size="56")
    assert len(endurance) >= 1
    for b in endurance:
        assert b["size"] == "56"


def test_list_all_bikes():
    """Verify list_all_bikes returns distinct strings."""
    models = list_all_bikes()
    assert len(models) >= 5
    assert any("Specialized" in m for m in models)
    assert any("Trek" in m for m in models)
