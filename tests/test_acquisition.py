"""Unit and regression tests for truck acquisition and batch procurement engine."""
import pytest

from simulator.primitives import SimulatorValidationError
from simulator.models import FinancingAssumptions, ProcurementAssumptions
from simulator.acquisition import (
    LANDED_COST_PRESETS,
    DEFAULT_BATCH_STEP,
    calculate_purchasable_trucks,
    evaluate_batch_procurement,
    evaluate_procurement_from_assumptions,
    find_earliest_affordable_month,
)


def test_landed_cost_presets():
    """Verify standard presets match Section 4.2 / Section 13 specification."""
    assert LANDED_COST_PRESETS["Best"] == 38_000_000.0
    assert LANDED_COST_PRESETS["Average"] == 40_000_000.0
    assert LANDED_COST_PRESETS["Worst"] == 42_000_000.0
    assert DEFAULT_BATCH_STEP == 5


def test_cannot_buy_partial_batch():
    """Verify that trucks are only purchased in discrete multiples of batch_step (5, 10, ...).
    Partial quantities (e.g. 6, 7, 8, 9) must never be purchased.
    """
    unit_cost = 40_000_000.0
    reserve = 0.0

    # 160M cash = exactly 4 trucks affordable -> but batch step is 5 -> purchasable = 0
    assert calculate_purchasable_trucks(160_000_000.0, reserve, unit_cost, batch_step=5) == 0

    # 200M cash = exactly 5 trucks affordable -> purchasable = 5
    assert calculate_purchasable_trucks(200_000_000.0, reserve, unit_cost, batch_step=5) == 5

    # 360M cash = 9 trucks affordable -> purchasable = 5 (waits for 10)
    assert calculate_purchasable_trucks(360_000_000.0, reserve, unit_cost, batch_step=5) == 5

    # 400M cash = 10 trucks affordable -> purchasable = 10
    assert calculate_purchasable_trucks(400_000_000.0, reserve, unit_cost, batch_step=5) == 10


def test_cash_reserve_strictly_preserved():
    """Verify cash reserve is preserved and cannot be consumed by batch procurement."""
    unit_cost = 40_000_000.0
    batch_step = 5
    reserve = 20_000_000.0

    # Total cash 210M: although 210M >= 200M (5 trucks), net cash is 190M (< 200M).
    # Buying 5 trucks would reduce cash to 10M, violating the 20M reserve.
    assert calculate_purchasable_trucks(210_000_000.0, reserve, unit_cost, batch_step) == 0

    # Total cash 220M: net cash is 200M. Exactly 5 trucks can be purchased.
    assert calculate_purchasable_trucks(220_000_000.0, reserve, unit_cost, batch_step) == 5


def test_evaluate_batch_procurement_shortfall_and_next_batch():
    """Section 6: Calculate next required capital and cash shortfall when batch cannot be ordered."""
    landed_cost = 40_000_000.0
    reserve = 20_000_000.0
    available_cash = 175_000_000.0

    eval_result = evaluate_batch_procurement(
        available_cash=available_cash,
        reserve=reserve,
        landed_cost=landed_cost,
        batch_step=5,
    )

    # 175M total cash with 20M reserve: net cash = 155M.
    # 5 trucks cost 200M -> cannot afford even 1 batch.
    assert not eval_result.is_batch_affordable
    assert eval_result.purchasable_trucks == 0
    assert eval_result.affordable_trucks_raw == 3  # 155M / 40M = 3.875
    assert eval_result.next_batch_trucks == 5
    # Required cash to buy 5 trucks while keeping 20M reserve = 200M + 20M = 220M
    assert eval_result.next_batch_required_cash == 220_000_000.0
    # Shortfall = 220M - 175M = 45M
    assert eval_result.cash_shortfall == 45_000_000.0
    assert eval_result.remaining_cash == 175_000_000.0


def test_evaluate_batch_procurement_with_contingency():
    """Verify contingency rate and fixed contingency addition to landed cost."""
    landed_cost = 40_000_000.0
    contingency_rate = 0.05  # +5%
    contingency_amount = 500_000.0  # +500k
    # Effective unit cost = 40M * 1.05 + 500k = 42M + 500k = 42.5M
    reserve = 10_000_000.0

    eval_result = evaluate_batch_procurement(
        available_cash=500_000_000.0,
        reserve=reserve,
        landed_cost=landed_cost,
        contingency_rate=contingency_rate,
        contingency_amount=contingency_amount,
        batch_step=5,
    )

    assert eval_result.unit_cost == 42_500_000.0
    # Net cash = 490M
    # Raw affordable = 490M / 42.5M = 11.529 -> 11 trucks
    # Purchasable = (11 // 5) * 5 = 10 trucks
    assert eval_result.purchasable_trucks == 10
    assert eval_result.total_batch_cost == 10 * 42_500_000.0  # 425M
    assert eval_result.remaining_cash == 500_000_000.0 - 425_000_000.0  # 75M
    assert eval_result.unallocated_cash_after_reserve == 65_000_000.0


def test_find_earliest_affordable_month():
    """Section 6: Show the earliest month when the next batch becomes affordable."""
    unit_cost = 40_000_000.0
    reserve = 20_000_000.0
    # Required for 5 trucks + 20M reserve = 220M
    projected_cash_list = [50_000_000.0, 100_000_000.0, 190_000_000.0, 225_000_000.0, 300_000_000.0]
    month_idx = find_earliest_affordable_month(projected_cash_list, reserve, unit_cost, batch_step=5)
    assert month_idx == 3  # month index 3 has 225M >= 220M

    # Dictionary representation with 1-based months
    projected_cash_dict = {
        1: 50_000_000.0,
        2: 120_000_000.0,
        3: 180_000_000.0,
        4: 240_000_000.0,
    }
    month_dict = find_earliest_affordable_month(projected_cash_dict, reserve, unit_cost, batch_step=5)
    assert month_dict == 4

    # Target batch never affordable within horizon
    short_cash_list = [50_000_000.0, 80_000_000.0, 150_000_000.0]
    assert find_earliest_affordable_month(short_cash_list, reserve, unit_cost, batch_step=5) is None


def test_acquisition_invalid_inputs():
    """Verify input validation errors."""
    with pytest.raises(SimulatorValidationError):
        calculate_purchasable_trucks(-100.0, 0.0, 40_000_000.0)

    with pytest.raises(SimulatorValidationError):
        calculate_purchasable_trucks(100_000.0, 0.0, 0.0)

    with pytest.raises(SimulatorValidationError):
        calculate_purchasable_trucks(100_000.0, 0.0, 40_000_000.0, batch_step=0)


def test_evaluate_from_assumptions():
    financing = FinancingAssumptions(bank_loan_amount=500_000_000.0, min_cash_reserve=20_000_000.0)
    procurement = ProcurementAssumptions(landed_cost=40_000_000.0, batch_step=5)

    eval_result = evaluate_procurement_from_assumptions(500_000_000.0, financing, procurement)
    # Available = 500M, Reserve = 20M, Net = 480M. 480M / 40M = 12 trucks. Purchasable = 10 trucks (400M).
    assert eval_result.purchasable_trucks == 10
    assert eval_result.total_batch_cost == 400_000_000.0
    assert eval_result.remaining_cash == 100_000_000.0
