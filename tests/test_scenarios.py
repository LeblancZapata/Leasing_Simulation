"""Unit tests for simulator/scenarios.py (Section 13 & Step 12)."""
import pytest
import pandas as pd

from simulator.primitives import SimulatorValidationError
from simulator.scenarios import (
    DEFAULT_SCENARIO_COSTS,
    DEFAULT_SCENARIO_RATES,
    DEFAULT_SCENARIO_TERMS,
    run_scenario_matrix,
    run_preset_comparison,
)


def test_scenario_matrix_dimensions_and_columns():
    df = run_scenario_matrix()
    # 3 costs x 3 rates x 4 terms = 36 rows
    assert len(df) == 36

    expected_cols = [
        "Scenario Cost",
        "Truck Cost (FCFA)",
        "Financing Rate",
        "Lease Term (Mos)",
        "Monthly Debt Service (500M)",
        "Sale Rec Price",
        "Sale Price Floor",
        "Lease Rec Price",
        "Lease Monthly Installment",
        "Recommended Strategy",
        "Best Risk-Adjusted NPV",
    ]
    for col in expected_cols:
        assert col in df.columns


def test_scenario_matrix_determinism():
    df1 = run_scenario_matrix()
    df2 = run_scenario_matrix()
    pd.testing.assert_frame_equal(df1, df2)


def test_preset_comparison():
    df_preset = run_preset_comparison(rate=0.20, term=24)
    assert len(df_preset) == 3
    # Check that truck costs correspond to 38M, 40M, 42M
    costs = df_preset["Truck Cost (FCFA)"].tolist()
    assert costs == [38_000_000.0, 40_000_000.0, 42_000_000.0]

    # As truck landed cost increases, recommended sale price must increase
    sale_prices = df_preset["Sale Rec Price"].tolist()
    assert sale_prices[0] < sale_prices[1] < sale_prices[2]


def test_scenario_matrix_custom_subsets():
    df = run_scenario_matrix(
        truck_costs={"Standard": 40_000_000.0},
        financing_rates=[0.20],
        lease_terms=[12, 24],
    )
    assert len(df) == 2


def test_scenario_matrix_invalid_inputs():
    with pytest.raises(SimulatorValidationError):
        run_scenario_matrix(truck_costs={"Invalid": -10_000_000.0})

    with pytest.raises(SimulatorValidationError):
        run_scenario_matrix(financing_rates=[1.5])

