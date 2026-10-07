"""Unit and regression tests for leasing and installment engine."""
import pytest

from simulator.primitives import SimulatorValidationError
from simulator.lease import (
    ALLOWED_LEASE_TERMS,
    MINIMUM_LEASE_DEPOSIT,
    calculate_lease_price_first,
    calculate_lease_payment_first,
    calculate_dynamic_recommended_lease_price,
    lease_schedule_to_dataframe,
)


def test_allowed_terms_and_rejections():
    """Section 8 & 15: V1 supports exactly four terms (6, 12, 18, 24 months)."""
    assert ALLOWED_LEASE_TERMS == (6, 12, 18, 24)

    # Valid terms execute cleanly
    for term in [6, 12, 18, 24]:
        res = calculate_lease_price_first(
            total_contract_price=50_000_000.0,
            initial_deposit=10_000_000.0,
            term_months=term,
            truck_cost=40_000_000.0,
        )
        assert res.term_months == term
        assert len(res.rows) == term

    # Invalid terms rejected
    for invalid_term in [0, 5, 8, 10, 15, 36, 48]:
        with pytest.raises(SimulatorValidationError):
            calculate_lease_price_first(
                total_contract_price=50_000_000.0,
                initial_deposit=10_000_000.0,
                term_months=invalid_term,
                truck_cost=40_000_000.0,
            )


def test_minimum_deposit_rules():
    """Section 8 & 15: Initial deposit cannot be below 10M FCFA."""
    # Exactly 10M accepted
    res_10m = calculate_lease_price_first(
        total_contract_price=50_000_000.0,
        initial_deposit=10_000_000.0,
        term_months=12,
        truck_cost=40_000_000.0,
    )
    assert res_10m.initial_deposit == 10_000_000.0

    # Above 10M accepted
    res_25m = calculate_lease_price_first(
        total_contract_price=55_000_000.0,
        initial_deposit=25_000_000.0,
        term_months=12,
        truck_cost=40_000_000.0,
    )
    assert res_25m.initial_deposit == 25_000_000.0

    # Below 10M rejected
    with pytest.raises(SimulatorValidationError):
        calculate_lease_price_first(
            total_contract_price=50_000_000.0,
            initial_deposit=9_999_999.0,
            term_months=12,
            truck_cost=40_000_000.0,
        )

    with pytest.raises(SimulatorValidationError):
        calculate_lease_price_first(
            total_contract_price=50_000_000.0,
            initial_deposit=0.0,
            term_months=12,
            truck_cost=40_000_000.0,
        )


def test_price_first_calculation_and_totals():
    """Section 8.1 Direction 1: Price-first calculation and schedule totality."""
    contract_price = 58_000_000.0
    deposit = 10_000_000.0
    term = 24
    truck_cost = 40_000_000.0

    res = calculate_lease_price_first(
        total_contract_price=contract_price,
        initial_deposit=deposit,
        term_months=term,
        truck_cost=truck_cost,
    )

    # Financed balance = 58M - 10M = 48M
    assert res.financed_balance == 48_000_000.0
    # Monthly installment = 48M / 24 = 2,000,000
    assert res.monthly_installment == 2_000_000.0

    # Payment schedule totals correctly
    assert res.total_contractual_receipts == contract_price
    sum_installments = sum(row.installment for row in res.rows)
    assert deposit + sum_installments == pytest.approx(contract_price)

    # Schedule continuity: final closing receivable is 0
    assert res.rows[-1].closing_receivable == 0.0
    assert res.rows[0].opening_receivable == res.financed_balance


def test_payment_capacity_first_calculation():
    """Section 8.1 Direction 2: Payment-capacity-first calculation."""
    max_payment = 2_500_000.0
    deposit = 10_000_000.0
    term = 12
    truck_cost = 40_000_000.0

    res = calculate_lease_payment_first(
        max_monthly_payment=max_payment,
        initial_deposit=deposit,
        term_months=term,
        truck_cost=truck_cost,
    )

    # Financed balance = 2.5M * 12 = 30M
    assert res.financed_balance == 30_000_000.0
    # Total contract price = 10M + 30M = 40M
    assert res.total_contract_price == 40_000_000.0
    assert res.monthly_installment == max_payment
    assert res.total_contractual_receipts == 40_000_000.0
    assert res.rows[-1].closing_receivable == 0.0


def test_break_even_and_npv_irr():
    """Verify break-even monthly payment, NPV, and IRR."""
    truck_cost = 40_000_000.0
    deposit = 10_000_000.0
    term = 12
    upfront_costs = 2_000_000.0  # GPS, legal, insurance
    contract_price = 54_000_000.0

    res = calculate_lease_price_first(
        total_contract_price=contract_price,
        initial_deposit=deposit,
        term_months=term,
        truck_cost=truck_cost,
        upfront_protection_costs=upfront_costs,
        discount_rate=0.20,
    )

    # Total cost = 40M + 2M = 42M
    assert res.total_costs == 42_000_000.0
    # Break-even contract price = 42M
    assert res.break_even_contract_price == 42_000_000.0
    # Break-even payment = (42M - 10M) / 12 = 32M / 12 = 2,666,666.67
    assert res.break_even_payment == pytest.approx(32_000_000.0 / 12.0)

    # Net profit = 54M - 42M = 12M
    assert res.net_profit == 12_000_000.0

    # NPV must be positive because return exceeds 20% discount rate
    assert res.npv > 0.0

    # IRR must be positive and valid
    assert res.irr_annualized is not None
    assert res.irr_annualized > 0.20


def test_early_payoff_scenario():
    """Verify early payoff option recalculates and terminates receivable."""
    res = calculate_lease_price_first(
        total_contract_price=58_000_000.0,
        initial_deposit=10_000_000.0,
        term_months=12,
        truck_cost=40_000_000.0,
        early_payoff_month=6,
    )

    # At month 6, full remaining balance is paid
    assert res.rows[5].closing_receivable == 0.0
    # Subsequent months have 0 installment and 0 receivable
    for row in res.rows[6:]:
        assert row.installment == 0.0
        assert row.closing_receivable == 0.0


def test_dynamic_recommended_lease_price():
    """Verify dynamic pricing from target return, term, and costs."""
    truck_cost = 40_000_000.0
    deposit = 10_000_000.0
    rec_price_12m = calculate_dynamic_recommended_lease_price(
        truck_cost=truck_cost,
        initial_deposit=deposit,
        term_months=12,
        target_annual_return=0.25,
    )
    # Capital = 40M, 25% return over 12 months = 10M -> 50M
    assert rec_price_12m == 50_000_000.0

    # 24 months = 2 years -> 40M * (1 + 0.50) = 60M
    rec_price_24m = calculate_dynamic_recommended_lease_price(
        truck_cost=truck_cost,
        initial_deposit=deposit,
        term_months=24,
        target_annual_return=0.25,
    )
    assert rec_price_24m == 60_000_000.0


def test_lease_schedule_dataframe():
    """Verify DataFrame export structure."""
    res = calculate_lease_price_first(
        total_contract_price=54_000_000.0,
        initial_deposit=10_000_000.0,
        term_months=6,
        truck_cost=40_000_000.0,
    )
    df = lease_schedule_to_dataframe(res)
    assert len(df) == 6
    assert list(df.columns) == ["Month", "Opening Receivable", "Installment", "Closing Receivable", "Cumulative Recovered", "Net Cash Flow"]


def test_generate_client_lease_options_30m_deposit():
    """Verify that a large deposit of 30M only offers short terms (6m, 12m) and excludes 18m/24m."""
    from simulator.lease import generate_client_lease_options

    options = generate_client_lease_options(truck_cost=40_000_000.0, initial_deposit=30_000_000.0)
    assert len(options) == 4

    opt_by_term = {opt.term_months: opt for opt in options}

    # 6 months and 12 months are offered
    assert opt_by_term[6].is_offered is True
    assert opt_by_term[12].is_offered is True

    # 18 months and 24 months are NOT offered
    assert opt_by_term[18].is_offered is False
    assert opt_by_term[24].is_offered is False
    assert "Non proposé" in opt_by_term[18].rejection_reason
    assert "Non proposé" in opt_by_term[24].rejection_reason


def test_generate_client_lease_options_12m_deposit():
    """Verify that a standard 12M deposit offers 12m, 18m, and 24m (recommending 24m)."""
    from simulator.lease import generate_client_lease_options

    options = generate_client_lease_options(truck_cost=40_000_000.0, initial_deposit=12_000_000.0)
    opt_by_term = {opt.term_months: opt for opt in options}

    assert opt_by_term[12].is_offered is True
    assert opt_by_term[18].is_offered is True
    assert opt_by_term[24].is_offered is True
    assert opt_by_term[24].is_recommended is True


def test_generate_client_lease_options_under_10m():
    """Verify that deposits under 10M are flagged with minimum deposit requirement."""
    from simulator.lease import generate_client_lease_options

    options = generate_client_lease_options(truck_cost=40_000_000.0, initial_deposit=8_000_000.0)
    for opt in options:
        assert opt.is_offered is False
        assert "10 000 000 FCFA" in opt.rejection_reason
