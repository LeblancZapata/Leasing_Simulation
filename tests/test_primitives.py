"""Comprehensive unit tests for financial primitives, helper functions, and validation."""
import pytest
import math

from simulator.primitives import (
    SimulatorValidationError,
    round_currency,
    format_fcfa,
    parse_fcfa,
    annual_to_monthly_rate,
    monthly_to_annual_rate,
    format_pct,
    month_to_calendar,
    format_month_label,
    validate_positive_number,
    validate_rate,
    validate_lease_term,
    validate_lease_deposit,
    validate_batch_step,
)

from simulator.models import (
    FinancingAssumptions,
    ProcurementAssumptions,
    CashSaleAssumptions,
    LeaseAssumptions,
    ExploitationAssumptions,
    ProtectionCostConfig,
    ProtectionCostItem,
    TaxConfig,
)


# ===========================================================================
# Currency / Money Primitives
# ===========================================================================

def test_round_currency():
    assert round_currency(1234.56) == 1235.0
    assert round_currency(1234.4) == 1234.0
    assert round_currency(1234.5678, decimals=2) == 1234.57
    with pytest.raises(SimulatorValidationError):
        round_currency(float("nan"))
    with pytest.raises(SimulatorValidationError):
        round_currency(float("inf"))


def test_format_fcfa():
    assert format_fcfa(500_000_000) == "500,000,000 FCFA"
    assert format_fcfa(40_000_000, include_symbol=False) == "40,000,000"
    assert format_fcfa(40_000_000, compact=True) == "40M FCFA"
    assert format_fcfa(1_500_000_000, compact=True) == "1.50B FCFA"
    assert format_fcfa(500_000, compact=True) == "500k FCFA"
    assert format_fcfa(-10_000_000, compact=True) == "-10M FCFA"
    assert format_fcfa(float("nan")) == "N/A"


def test_parse_fcfa():
    assert parse_fcfa("500M") == 500_000_000.0
    assert parse_fcfa("40,000,000 FCFA") == 40_000_000.0
    assert parse_fcfa("1.5B") == 1_500_000_000.0
    assert parse_fcfa("250k") == 250_000.0
    assert parse_fcfa(50_000_000) == 50_000_000.0
    assert parse_fcfa(" 38 M ") == 38_000_000.0

    with pytest.raises(SimulatorValidationError):
        parse_fcfa("")
    with pytest.raises(SimulatorValidationError):
        parse_fcfa("invalid_amount")


# ===========================================================================
# Percentage and Interest Rate Primitives
# ===========================================================================

def test_annual_to_monthly_rate():
    assert annual_to_monthly_rate(0.12) == pytest.approx(0.01)
    assert annual_to_monthly_rate(0.20) == pytest.approx(0.20 / 12.0)
    assert annual_to_monthly_rate(0.0) == 0.0

    with pytest.raises(SimulatorValidationError):
        annual_to_monthly_rate(-0.05)
    with pytest.raises(SimulatorValidationError):
        annual_to_monthly_rate(float("nan"))


def test_monthly_to_annual_rate():
    assert monthly_to_annual_rate(0.01) == pytest.approx(0.12)
    assert monthly_to_annual_rate(0.0) == 0.0

    with pytest.raises(SimulatorValidationError):
        monthly_to_annual_rate(-0.01)


def test_format_pct():
    assert format_pct(0.20) == "20.00%"
    assert format_pct(0.055, decimals=1) == "5.5%"
    assert format_pct(float("nan")) == "N/A"


# ===========================================================================
# Date and Simulation Month Primitives
# ===========================================================================

def test_month_to_calendar():
    assert month_to_calendar(0, start_year=2026, start_month=1) == (2026, 1)
    assert month_to_calendar(1, start_year=2026, start_month=1) == (2026, 1)
    assert month_to_calendar(12, start_year=2026, start_month=1) == (2026, 12)
    assert month_to_calendar(13, start_year=2026, start_month=1) == (2027, 1)
    assert month_to_calendar(36, start_year=2026, start_month=1) == (2028, 12)

    with pytest.raises(SimulatorValidationError):
        month_to_calendar(-1)


def test_format_month_label():
    assert format_month_label(0, start_year=2026, start_month=1) == "Month 0 (Initial - Jan 2026)"
    assert format_month_label(1, start_year=2026, start_month=1) == "Month 1 (Jan 2026)"
    assert format_month_label(13, start_year=2026, start_month=1) == "Month 13 (Jan 2027)"


# ===========================================================================
# Common Validation Rules
# ===========================================================================

def test_validate_positive_number():
    assert validate_positive_number("Cash", 0.0, allow_zero=True) == 0.0
    assert validate_positive_number("Cash", 100.0) == 100.0

    with pytest.raises(SimulatorValidationError):
        validate_positive_number("Cost", -1.0)

    with pytest.raises(SimulatorValidationError):
        validate_positive_number("Cost", 0.0, allow_zero=False)

    with pytest.raises(SimulatorValidationError):
        validate_positive_number("Cost", float("nan"))


def test_validate_rate():
    assert validate_rate("Rate", 0.20) == 0.20
    assert validate_rate("Rate", 0.0) == 0.0
    assert validate_rate("Rate", 1.0) == 1.0

    with pytest.raises(SimulatorValidationError):
        validate_rate("Rate", -0.01)

    with pytest.raises(SimulatorValidationError):
        validate_rate("Rate", 1.05)


def test_validate_lease_term():
    for term in [6, 12, 18, 24]:
        assert validate_lease_term(term) == term

    for invalid_term in [0, 5, 10, 36, 48]:
        with pytest.raises(SimulatorValidationError):
            validate_lease_term(invalid_term)


def test_validate_lease_deposit():
    assert validate_lease_deposit(10_000_000.0) == 10_000_000.0
    assert validate_lease_deposit(15_000_000.0) == 15_000_000.0

    with pytest.raises(SimulatorValidationError):
        validate_lease_deposit(9_999_999.0)

    with pytest.raises(SimulatorValidationError):
        validate_lease_deposit(0.0)


def test_validate_batch_step():
    assert validate_batch_step(0, batch_step=5) == 0
    assert validate_batch_step(5, batch_step=5) == 5
    assert validate_batch_step(15, batch_step=5) == 15

    with pytest.raises(SimulatorValidationError):
        validate_batch_step(3, batch_step=5)

    with pytest.raises(SimulatorValidationError):
        validate_batch_step(-5, batch_step=5)


# ===========================================================================
# Domain Dataclasses Initialization and Business Rules
# ===========================================================================

def test_financing_assumptions_validation():
    fa = FinancingAssumptions()
    assert fa.bank_loan_amount == 500_000_000.0
    assert fa.annual_financing_rate == 0.15
    assert fa.monthly_interest_rate == pytest.approx(0.15 / 12.0)

    # Invalid loan term
    with pytest.raises(SimulatorValidationError):
        FinancingAssumptions(loan_term_months=0)

    # Negative rate
    with pytest.raises(SimulatorValidationError):
        FinancingAssumptions(annual_financing_rate=-0.1)


def test_procurement_assumptions_validation():
    pa = ProcurementAssumptions(landed_cost=40_000_000.0, batch_step=5, contingency_rate=0.05, contingency_amount=500_000.0)
    assert pa.effective_unit_cost == 40_000_000.0 * 1.05 + 500_000.0

    with pytest.raises(SimulatorValidationError):
        ProcurementAssumptions(landed_cost=-10.0)

    with pytest.raises(SimulatorValidationError):
        ProcurementAssumptions(batch_step=0)


def test_lease_assumptions_validation():
    # Valid default
    la = LeaseAssumptions(term_months=24, initial_deposit=10_000_000.0)
    assert la.term_months == 24

    # Deposit below 10M FCFA rejected
    with pytest.raises(SimulatorValidationError):
        LeaseAssumptions(term_months=24, initial_deposit=8_000_000.0)

    # Invalid lease term (not 6, 12, 18, 24)
    with pytest.raises(SimulatorValidationError):
        LeaseAssumptions(term_months=36, initial_deposit=10_000_000.0)

    # Total contract price below initial deposit rejected
    with pytest.raises(SimulatorValidationError):
        LeaseAssumptions(
            term_months=12,
            initial_deposit=15_000_000.0,
            total_contract_price=12_000_000.0,
        )


def test_exploitation_assumptions_calculation():
    ea = ExploitationAssumptions(
        net_monthly_profit_per_truck=2_500_000.0,
        downtime_allowance_rate=0.10,
        gps_monthly_cost=15_000.0,
        other_monthly_overhead=35_000.0,
    )
    # (2,500,000 * 0.90) - 15,000 - 35,000 = 2,250,000 - 50,000 = 2,200,000
    assert ea.effective_monthly_cash_per_truck == 2_200_000.0


def test_protection_costs_config():
    pc = ProtectionCostConfig()
    upfront = pc.total_upfront_fixed_protection()
    assert upfront > 0.0
    var_rate = pc.total_variable_protection_rate()
    assert var_rate == pytest.approx(0.05)  # default_reserve (5%) enabled, payment processing disabled by default


def test_tax_config():
    tc = TaxConfig()
    assert tc.vat_rate == 0.1925
    assert not tc.vat_recoverable
    assert tc.corporate_income_tax_rate == 0.30
