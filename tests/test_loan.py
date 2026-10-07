"""Unit and regression tests for loan amortization engine."""
import pytest
import numpy_financial as npf

from simulator.primitives import SimulatorValidationError, annual_to_monthly_rate
from simulator.models import FinancingAssumptions
from simulator.loan import (
    calculate_monthly_payment,
    generate_amortization_schedule,
    generate_loan_schedule_from_assumptions,
    schedule_to_dataframe,
)


def test_standard_loan_calculation_500m_20pct_36m():
    """Section 5.1 Required example test:
    At P = 500M, annual rate = 20%, term = 36 months, calculate monthly payment
    and total repayment automatically without hardcoding.
    """
    principal = 500_000_000.0
    annual_rate = 0.20
    term_months = 36

    # Verify against numpy-financial pmt
    monthly_rate = annual_to_monthly_rate(annual_rate)
    expected_pmt = float(npf.pmt(monthly_rate, term_months, -principal))

    payment = calculate_monthly_payment(principal, annual_rate, term_months)
    assert payment == pytest.approx(expected_pmt, rel=1e-5)

    schedule = generate_amortization_schedule(principal, annual_rate, term_months)
    assert len(schedule.rows) == term_months
    assert schedule.monthly_payment == pytest.approx(expected_pmt, rel=1e-5)

    # Total principal must equal original loan
    assert schedule.total_principal == pytest.approx(principal, rel=1e-5)

    # Final closing balance must be exactly 0
    assert schedule.rows[-1].closing_balance == 0.0

    # Total repayment and total interest consistency
    assert schedule.total_payment == pytest.approx(schedule.total_principal + schedule.total_interest, rel=1e-5)


def test_zero_rate_loan():
    """Loan with 0% interest rate."""
    principal = 120_000_000.0
    annual_rate = 0.0
    term_months = 12

    payment = calculate_monthly_payment(principal, annual_rate, term_months)
    assert payment == 10_000_000.0

    schedule = generate_amortization_schedule(principal, annual_rate, term_months)
    assert len(schedule.rows) == 12
    assert schedule.total_interest == 0.0
    assert schedule.total_principal == pytest.approx(principal)
    assert schedule.total_payment == pytest.approx(principal)
    assert schedule.rows[-1].closing_balance == 0.0

    for row in schedule.rows:
        assert row.interest == 0.0
        assert row.principal == pytest.approx(10_000_000.0)


def test_zero_principal_loan():
    """Loan with zero principal."""
    payment = calculate_monthly_payment(0.0, 0.20, 36)
    assert payment == 0.0

    schedule = generate_amortization_schedule(0.0, 0.20, 36)
    assert len(schedule.rows) == 0
    assert schedule.total_payment == 0.0
    assert schedule.total_principal == 0.0


def test_schedule_continuity_and_balances():
    """Verify that each month's opening balance matches the previous month's closing balance."""
    principal = 250_000_000.0
    annual_rate = 0.18
    term_months = 24

    schedule = generate_amortization_schedule(principal, annual_rate, term_months)
    assert schedule.rows[0].opening_balance == pytest.approx(principal)

    for i in range(1, len(schedule.rows)):
        prev_closing = schedule.rows[i - 1].closing_balance
        curr_opening = schedule.rows[i].opening_balance
        assert curr_opening == pytest.approx(prev_closing, abs=1e-4)

    assert schedule.rows[-1].closing_balance == 0.0
    assert schedule.total_principal == pytest.approx(principal, abs=1e-4)


def test_loan_invalid_inputs():
    """Verify invalid parameters trigger domain validation errors."""
    with pytest.raises(SimulatorValidationError):
        calculate_monthly_payment(-100_000, 0.10, 12)

    with pytest.raises(SimulatorValidationError):
        calculate_monthly_payment(100_000, -0.05, 12)

    with pytest.raises(SimulatorValidationError):
        calculate_monthly_payment(100_000, 0.10, 0)


def test_generate_from_assumptions_and_dataframe():
    """Verify integration with FinancingAssumptions and dataframe output."""
    assumptions = FinancingAssumptions(
        bank_loan_amount=400_000_000.0,
        annual_financing_rate=0.15,
        loan_term_months=36,
    )
    schedule = generate_loan_schedule_from_assumptions(assumptions)
    assert schedule.total_principal == pytest.approx(400_000_000.0)

    df = schedule_to_dataframe(schedule)
    assert len(df) == 36
    assert list(df.columns) == ["Month", "Opening Balance", "Payment", "Interest", "Principal", "Closing Balance"]
    assert df["Closing Balance"].iloc[-1] == 0.0
