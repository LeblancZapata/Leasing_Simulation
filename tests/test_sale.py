"""Unit and regression tests for cash-sale pricing engine."""
import pytest

from simulator.primitives import SimulatorValidationError
from simulator.sale import (
    MARKET_BENCHMARK_PRICES,
    calculate_financing_carry,
    calculate_price_floor,
    calculate_recommended_price,
    evaluate_cash_sale_pricing,
    evaluate_sale_price_economics,
    generate_market_comparison_table,
)


def test_reference_recommended_price_40m_20pct():
    """Section 7 Specification Reference:
    With a 40M landed cost, a 20% target markup produces 48M before additional transaction/financing costs.
    """
    landed_cost = 40_000_000.0
    target_markup = 0.20

    rec_price = calculate_recommended_price(
        landed_cost=landed_cost,
        target_markup=target_markup,
        financing_carry=0.0,
        transaction_costs=0.0,
        risk_reserve=0.0,
    )
    assert rec_price == 48_000_000.0


def test_preset_costs_recommended_pricing_38m_40m_42m():
    """Verify pricing behavior across all three scenario presets (38M, 40M, 42M)."""
    # Best Case (38M)
    rec_38m = calculate_recommended_price(38_000_000.0, target_markup=0.20)
    assert rec_38m == 38_000_000.0 * 1.20  # 45.6M

    # Average Case (40M)
    rec_40m = calculate_recommended_price(40_000_000.0, target_markup=0.20)
    assert rec_40m == 48_000_000.0

    # Worst Case (42M)
    rec_42m = calculate_recommended_price(42_000_000.0, target_markup=0.20)
    assert rec_42m == 42_000_000.0 * 1.20  # 50.4M


def test_financing_carry_and_holding_period():
    """Verify financing debt carrying costs across different holding periods."""
    capital = 40_000_000.0
    annual_rate = 0.20

    # Instantaneous sale (holding period = 0)
    carry_0 = calculate_financing_carry(capital, annual_rate, holding_period_months=0)
    assert carry_0 == 0.0

    # 1 month holding period: 40M * (0.20 / 12) = 666,666.67
    carry_1 = calculate_financing_carry(capital, annual_rate, holding_period_months=1)
    assert carry_1 == pytest.approx(40_000_000.0 * (0.20 / 12.0), abs=0.01)

    # 3 months holding period: 3x
    carry_3 = calculate_financing_carry(capital, annual_rate, holding_period_months=3)
    assert carry_3 == pytest.approx(carry_1 * 3.0, abs=0.01)


def test_price_floor_calculation():
    """Verify price floor accumulates landed cost, carrying costs, selling costs, reserve, and minimum profit."""
    landed_cost = 40_000_000.0
    acquisition_costs = 500_000.0
    financing_carry = 666_667.0
    selling_costs = 300_000.0
    risk_reserve = 500_000.0
    minimum_profit = 1_000_000.0

    expected_floor = (
        landed_cost
        + acquisition_costs
        + financing_carry
        + selling_costs
        + risk_reserve
        + minimum_profit
    )
    floor_val = calculate_price_floor(
        landed_cost=landed_cost,
        acquisition_costs=acquisition_costs,
        financing_carry=financing_carry,
        selling_costs=selling_costs,
        risk_reserve=risk_reserve,
        minimum_profit=minimum_profit,
    )
    assert floor_val == expected_floor
    assert floor_val == 42_966_667.0


def test_evaluate_sale_price_economics():
    """Verify returns, gross margin, net margin, and floor compliance for customer offers."""
    pricing = evaluate_cash_sale_pricing(
        landed_cost=40_000_000.0,
        target_markup=0.20,
        holding_period_months=1,
        annual_financing_rate=0.20,
        acquisition_costs=0.0,
        selling_costs=200_000.0,
        transaction_costs=100_000.0,
        risk_reserve=500_000.0,
        minimum_profit=1_000_000.0,
    )

    # Offer at 46M (common market negotiation point mentioned in plan)
    offer_46m = evaluate_sale_price_economics(46_000_000.0, pricing)
    assert offer_46m.capital_tied_up == 40_000_000.0
    assert offer_46m.gross_profit == 6_000_000.0
    assert offer_46m.gross_margin == pytest.approx(6_000_000.0 / 46_000_000.0)
    assert offer_46m.capital_released == 46_000_000.0
    assert offer_46m.is_above_floor  # 46M > floor (~42.36M)

    # Offer below floor: 41M
    offer_41m = evaluate_sale_price_economics(41_000_000.0, pricing)
    assert not offer_41m.is_above_floor
    assert offer_41m.price_floor_delta < 0


def test_market_comparison_table():
    """Verify market benchmark table generates rows for 46M, 47M, 48M, 49M, and 50M."""
    pricing = evaluate_cash_sale_pricing(landed_cost=40_000_000.0, target_markup=0.20)
    df = generate_market_comparison_table(pricing)

    assert len(df) == len(MARKET_BENCHMARK_PRICES)
    assert list(df["Offer Price"]) == [46_000_000.0, 47_000_000.0, 48_000_000.0, 49_000_000.0, 50_000_000.0]
    assert "Gross Margin" in df.columns
    assert "Net Profit" in df.columns
    assert "Meets Floor?" in df.columns


def test_cash_sale_invalid_inputs():
    """Verify error checking for invalid cash-sale parameters."""
    with pytest.raises(SimulatorValidationError):
        calculate_price_floor(0.0)

    with pytest.raises(SimulatorValidationError):
        calculate_financing_carry(40_000_000.0, 0.20, holding_period_months=-1)

    with pytest.raises(SimulatorValidationError):
        calculate_recommended_price(40_000_000.0, target_markup=-0.1)

    with pytest.raises(SimulatorValidationError):
        evaluate_sale_price_economics(0.0, evaluate_cash_sale_pricing(40_000_000.0))
