"""End-to-End integration and QA test suite (Section 15 & Step 13)."""
import pytest
import pandas as pd

from simulator.primitives import (
    format_fcfa,
    format_pct,
    SimulatorValidationError,
)
from simulator.models import (
    FinancingAssumptions,
    ProcurementAssumptions,
    LeaseAssumptions,
    ExploitationAssumptions,
    ProtectionCostConfig,
)
from simulator.loan import generate_loan_schedule_from_assumptions
from simulator.acquisition import evaluate_procurement_from_assumptions
from simulator.sale import evaluate_cash_sale_pricing, evaluate_sale_price_economics
from simulator.lease import calculate_lease_price_first
from simulator.exploitation import evaluate_exploitation
from simulator.portfolio import StrategyType
from simulator.simulation import SimulationConfig, run_portfolio_simulation, simulation_to_dataframe
from simulator.metrics import compare_strategies
from simulator.scenarios import run_scenario_matrix


class TestEndToEndQAWorkflow:
    """Verifies complete end-to-end simulation lifecycle with benchmark business parameters."""

    def test_complete_simulation_workflow_benchmark(self):
        # 1. Global Financing: 500M loan at 20% over 36 months
        fin = FinancingAssumptions(
            bank_loan_amount=500_000_000.0,
            annual_financing_rate=0.20,
            loan_term_months=36,
            min_cash_reserve=20_000_000.0,
        )
        loan_sched = generate_loan_schedule_from_assumptions(fin)
        assert len(loan_sched.rows) == 36
        assert pytest.approx(loan_sched.rows[-1].closing_balance, abs=1.0) == 0.0

        # 2. Procurement: 40M landed cost, batch step 5
        proc = ProcurementAssumptions(
            landed_cost=40_000_000.0,
            batch_step=5,
        )
        eval_proc = evaluate_procurement_from_assumptions(
            available_cash=500_000_000.0,
            financing=fin,
            procurement=proc,
        )
        # (500M - 20M reserve) = 480M / 40M = 12 trucks -> 10 trucks purchased (batch step 5)
        assert eval_proc.purchasable_trucks == 10
        assert eval_proc.purchasable_trucks // eval_proc.batch_step == 2
        assert eval_proc.remaining_cash >= fin.min_cash_reserve

        # 3. Strategy Recommendation
        rec = compare_strategies(
            landed_cost=proc.landed_cost,
            annual_financing_rate=fin.annual_financing_rate,
            horizon_months=fin.loan_term_months,
            cash_sale_price=48_000_000.0,
            lease_term=24,
            lease_deposit=10_000_000.0,
            lease_contract_price=58_000_000.0,
            exploit_monthly_profit=2_500_000.0,
            required_reserve=fin.min_cash_reserve,
            batch_step=proc.batch_step,
        )
        assert rec.recommended_strategy in [StrategyType.LEASING, StrategyType.CASH_SALE, StrategyType.EXPLOITATION]
        assert rec.constraints_verified["lease_deposit_above_10m"] is True
        assert rec.constraints_verified["cash_reserve_preserved"] is True

        # 4. Multi-Year Portfolio Simulation (Leasing with reinvestment)
        sim_cfg = SimulationConfig(
            financing=fin,
            procurement=proc,
            primary_strategy=StrategyType.LEASING,
            lease=LeaseAssumptions(term_months=24, initial_deposit=10_000_000.0, total_contract_price=58_000_000.0),
            horizon_months=36,
            reinvest_cash=True,
        )
        sim_result = run_portfolio_simulation(sim_cfg)
        df_sim = simulation_to_dataframe(sim_result)

        # Invariant checks:
        # a. Final debt is 0 after 36 months
        assert sim_result.final_debt == 0.0
        # b. Minimum cash never went below 0
        assert sim_result.minimum_cash_experienced >= 0.0
        # c. Total trucks purchased is a multiple of 5
        assert sim_result.total_trucks_purchased % 5 == 0
        # d. Trajectory dataframe has 36 monthly rows (Month 1 to 36)
        assert len(df_sim) == 36

        # 5. Full 36-Scenario Matrix Execution
        df_matrix = run_scenario_matrix(
            loan_amount=fin.bank_loan_amount,
            loan_term_months=fin.loan_term_months,
            lease_deposit=10_000_000.0,
        )
        assert len(df_matrix) == 36
        assert not df_matrix.empty

    def test_deposit_boundary_invariants(self):
        # Exactly 10M is accepted
        lease_ok = calculate_lease_price_first(
            total_contract_price=58_000_000.0,
            initial_deposit=10_000_000.0,
            term_months=24,
            truck_cost=40_000_000.0,
        )
        assert lease_ok.initial_deposit == 10_000_000.0

        # 9,999,999.99 is rejected
        with pytest.raises(SimulatorValidationError):
            calculate_lease_price_first(
                total_contract_price=58_000_000.0,
                initial_deposit=9_999_999.99,
                term_months=24,
                truck_cost=40_000_000.0,
            )

    def test_simulation_reproducibility_and_determinism(self):
        fin = FinancingAssumptions(bank_loan_amount=500_000_000.0, annual_financing_rate=0.20, loan_term_months=36)
        proc = ProcurementAssumptions(landed_cost=40_000_000.0, batch_step=5)
        sim_cfg = SimulationConfig(
            financing=fin,
            procurement=proc,
            primary_strategy=StrategyType.EXPLOITATION,
            exploitation=ExploitationAssumptions(net_monthly_profit_per_truck=2_500_000.0),
            horizon_months=36,
            reinvest_cash=True,
        )
        res1 = run_portfolio_simulation(sim_cfg)
        res2 = run_portfolio_simulation(sim_cfg)

        assert res1.final_cash == res2.final_cash
        assert res1.final_debt == res2.final_debt
        assert res1.total_trucks_purchased == res2.total_trucks_purchased
        assert res1.cumulative_cash_generated == res2.cumulative_cash_generated
