"""Unit and regression tests for discrete monthly portfolio simulation engine."""
import pytest

from simulator.primitives import SimulatorValidationError
from simulator.models import (
    FinancingAssumptions,
    ProcurementAssumptions,
    LeaseAssumptions,
    ExploitationAssumptions,
    CashSaleAssumptions,
)
from simulator.portfolio import StrategyType, TruckState
from simulator.simulation import (
    SimulationConfig,
    run_portfolio_simulation,
    simulation_to_dataframe,
)


def test_portfolio_simulation_leasing_lifecycle():
    """Section 11 & 15: Deterministic monthly simulation for Strategy B (Leasing).
    Verifies debt payments, lease cash, reserve preservation, and final debt payoff.
    """
    financing = FinancingAssumptions(
        bank_loan_amount=500_000_000.0,
        annual_financing_rate=0.20,
        loan_term_months=36,
        starting_cash=0.0,
        min_cash_reserve=20_000_000.0,
    )
    procurement = ProcurementAssumptions(
        landed_cost=40_000_000.0,
        batch_step=5,
    )
    lease = LeaseAssumptions(
        term_months=24,
        initial_deposit=10_000_000.0,
        total_contract_price=58_000_000.0,
    )

    config = SimulationConfig(
        financing=financing,
        procurement=procurement,
        primary_strategy=StrategyType.LEASING,
        lease=lease,
        horizon_months=36,
        reinvest_cash=True,
    )

    result = run_portfolio_simulation(config)

    assert len(result.snapshots) == 36

    # Initial batch: 500M - 20M reserve = 480M -> 12 trucks -> 10 trucks (multiples of 5)
    assert len(result.trucks) >= 10
    initial_trucks = [t for t in result.trucks if t.acquisition_month == 0]
    assert len(initial_trucks) == 10

    # Debt decreases each month and hits exactly 0.0 at month 36
    assert result.final_debt == 0.0
    for s in result.snapshots:
        assert s.outflows_debt_service > 0.0

    # Cash reserve strictly preserved: no negative cash
    assert result.minimum_cash_experienced >= financing.min_cash_reserve
    for s in result.snapshots:
        assert s.closing_cash >= financing.min_cash_reserve

    # Reinvestment occurred and expanded fleet
    assert result.total_trucks_purchased >= 10
    assert result.reinvestment_batch_count >= 1


def test_simulation_reinvestment_toggle():
    """Verify that setting reinvest_cash=False freezes fleet size to the initial batch."""
    financing = FinancingAssumptions(
        bank_loan_amount=500_000_000.0,
        annual_financing_rate=0.20,
        loan_term_months=36,
        min_cash_reserve=20_000_000.0,
    )
    procurement = ProcurementAssumptions(landed_cost=40_000_000.0, batch_step=5)

    config = SimulationConfig(
        financing=financing,
        procurement=procurement,
        primary_strategy=StrategyType.LEASING,
        horizon_months=36,
        reinvest_cash=False,  # Reinvestment disabled
    )

    result = run_portfolio_simulation(config)
    assert result.total_trucks_purchased == 10
    assert result.reinvestment_batch_count == 1  # only initial batch
    for s in result.snapshots:
        assert s.reinvestment_trucks_purchased == 0
        assert s.total_trucks_owned == 10


def test_portfolio_simulation_exploitation():
    """Section 11 & 15: Deterministic monthly simulation for Strategy C (Exploitation)."""
    financing = FinancingAssumptions(
        bank_loan_amount=500_000_000.0,
        annual_financing_rate=0.20,
        loan_term_months=36,
        min_cash_reserve=20_000_000.0,
    )
    procurement = ProcurementAssumptions(landed_cost=40_000_000.0, batch_step=5)
    exploitation = ExploitationAssumptions(
        net_monthly_profit_per_truck=2_500_000.0,
        downtime_allowance_rate=0.0,
    )

    config = SimulationConfig(
        financing=financing,
        procurement=procurement,
        primary_strategy=StrategyType.EXPLOITATION,
        exploitation=exploitation,
        horizon_months=36,
        reinvest_cash=True,
    )

    result = run_portfolio_simulation(config)

    assert len(result.snapshots) == 36
    assert result.final_debt == 0.0

    # 10 initial trucks generate 25M/mo exploitation cash in month 1
    assert result.snapshots[0].inflows_exploitation == 25_000_000.0

    # Cash reserve strictly preserved
    assert result.minimum_cash_experienced >= financing.min_cash_reserve


def test_portfolio_simulation_cash_sale():
    """Section 11 & 15: Deterministic monthly simulation for Strategy A (Cash Sale)."""
    financing = FinancingAssumptions(
        bank_loan_amount=500_000_000.0,
        annual_financing_rate=0.20,
        loan_term_months=36,
        min_cash_reserve=20_000_000.0,
    )
    procurement = ProcurementAssumptions(landed_cost=40_000_000.0, batch_step=5)
    cash_sale = CashSaleAssumptions(
        target_markup=0.20,
        holding_period_months=1,
    )

    config = SimulationConfig(
        financing=financing,
        procurement=procurement,
        primary_strategy=StrategyType.CASH_SALE,
        cash_sale=cash_sale,
        horizon_months=12,
        reinvest_cash=False,
    )

    result = run_portfolio_simulation(config)

    # In month 1, initial 10 trucks are sold
    assert result.snapshots[0].inflows_sales > 0.0
    sold_trucks = [t for t in result.trucks if t.current_state == TruckState.SOLD]
    assert len(sold_trucks) == 10


def test_simulation_dataframe_export():
    """Verify conversion of simulation snapshots to a Pandas DataFrame."""
    financing = FinancingAssumptions(bank_loan_amount=500_000_000.0, loan_term_months=12)
    procurement = ProcurementAssumptions(landed_cost=40_000_000.0)
    config = SimulationConfig(financing=financing, procurement=procurement, horizon_months=12)

    result = run_portfolio_simulation(config)
    df = simulation_to_dataframe(result)

    assert len(df) == 12
    assert "Opening Cash" in df.columns
    assert "Debt Service" in df.columns
    assert "Closing Debt" in df.columns
    assert df["Closing Debt"].iloc[-1] == 0.0
