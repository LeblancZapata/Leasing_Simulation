"""Unit tests for the Business Analyst and Portfolio Optimizer engine."""
import pytest

from simulator.models import (
    FinancingAssumptions,
    ProcurementAssumptions,
    CashSaleAssumptions,
    LeaseAssumptions,
    ExploitationAssumptions,
    ProtectionCostConfig,
    TaxConfig,
)
from simulator.portfolio import StrategyType
from simulator.analyst import (
    evaluate_single_plan,
    run_business_analyst_optimizer,
    generate_analyst_insights,
)


@pytest.fixture
def base_assumptions():
    financing = FinancingAssumptions(
        bank_loan_amount=500_000_000.0,
        annual_financing_rate=0.12,
        loan_term_months=36,
        starting_cash=0.0,
        min_cash_reserve=50_000_000.0,
    )
    procurement = ProcurementAssumptions(
        landed_cost=40_000_000.0,
        batch_step=5,
    )
    cash_sale = CashSaleAssumptions(
        target_markup=0.20,
        holding_period_months=1,
    )
    lease = LeaseAssumptions(
        term_months=24,
        initial_deposit=12_000_000.0,
        total_contract_price=60_000_000.0,
    )
    exploitation = ExploitationAssumptions(
        net_monthly_profit_per_truck=3_000_000.0,
        downtime_allowance_rate=0.10,
    )
    protection_config = ProtectionCostConfig()
    tax_config = TaxConfig()
    return {
        "financing": financing,
        "procurement": procurement,
        "cash_sale": cash_sale,
        "lease": lease,
        "exploitation": exploitation,
        "protection_config": protection_config,
        "tax_config": tax_config,
    }


def test_evaluate_single_plan(base_assumptions):
    alloc = {
        StrategyType.EXPLOITATION: 0.50,
        StrategyType.LEASING: 0.30,
        StrategyType.CASH_SALE: 0.20,
    }
    plan = evaluate_single_plan(
        name="Test Hybrid Plan",
        allocation=alloc,
        description="Testing 50/30/20 mix",
        financing=base_assumptions["financing"],
        procurement=base_assumptions["procurement"],
        cash_sale=base_assumptions["cash_sale"],
        lease=base_assumptions["lease"],
        exploitation=base_assumptions["exploitation"],
        protection_config=base_assumptions["protection_config"],
        tax_config=base_assumptions["tax_config"],
        horizon_months=36,
        reinvest_cash=False,
    )

    assert plan.name == "Test Hybrid Plan"
    assert plan.total_trucks_operated == 10
    assert plan.total_net_profit > 0.0
    assert plan.final_cash > 0.0
    assert plan.min_cash_balance >= base_assumptions["financing"].min_cash_reserve
    assert plan.is_cash_reserve_preserved is True
    assert len(plan.pros) > 0


def test_run_business_analyst_optimizer(base_assumptions):
    result = run_business_analyst_optimizer(
        financing=base_assumptions["financing"],
        procurement=base_assumptions["procurement"],
        cash_sale=base_assumptions["cash_sale"],
        lease=base_assumptions["lease"],
        exploitation=base_assumptions["exploitation"],
        protection_config=base_assumptions["protection_config"],
        tax_config=base_assumptions["tax_config"],
        horizon_years=3,
        reinvest_cash=True,
    )

    assert "recommended_plan" in result
    assert "all_plans" in result
    assert len(result["all_plans"]) >= 5
    assert result["horizon_years"] == 3
    assert result["horizon_months"] == 36

    rec = result["recommended_plan"]
    assert rec.score >= result["all_plans"][-1].score
    assert rec.final_cash > 0

    insights = result["insights"]
    assert "debt_diagnosis" in insights
    assert "payoff_and_cash" in insights
    assert "real_world_warning" in insights
    assert "why_combine" in insights


def test_custom_allocation_in_optimizer(base_assumptions):
    custom_alloc = {
        StrategyType.EXPLOITATION: 0.70,
        StrategyType.LEASING: 0.20,
        StrategyType.CASH_SALE: 0.10,
    }
    result = run_business_analyst_optimizer(
        financing=base_assumptions["financing"],
        procurement=base_assumptions["procurement"],
        cash_sale=base_assumptions["cash_sale"],
        lease=base_assumptions["lease"],
        exploitation=base_assumptions["exploitation"],
        protection_config=base_assumptions["protection_config"],
        tax_config=base_assumptions["tax_config"],
        horizon_years=2,
        custom_allocation=custom_alloc,
        reinvest_cash=False,
    )

    assert result["custom_plan"] is not None
    assert result["custom_plan"].name == "Plan Personnalisé Utilisateur"
    assert result["horizon_months"] == 24

