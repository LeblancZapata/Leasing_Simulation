"""Unit and regression tests for simulator/metrics.py (Section 12 & 12.1)."""
import pytest
import pandas as pd

from simulator.primitives import SimulatorValidationError
from simulator.portfolio import StrategyType
from simulator.metrics import (
    calculate_roi,
    calculate_cash_on_cash,
    calculate_dscr,
    StrategyMetrics,
    StrategyRecommendation,
    compare_strategies,
)


class TestFinancialMetricFormulas:
    def test_calculate_roi_standard(self):
        roi = calculate_roi(net_profit=10_000_000.0, capital_invested=40_000_000.0)
        assert pytest.approx(roi, rel=1e-5) == 0.25

    def test_calculate_roi_zero_or_negative_capital(self):
        assert calculate_roi(net_profit=5_000_000.0, capital_invested=0.0) == 0.0
        assert calculate_roi(net_profit=5_000_000.0, capital_invested=-10_000.0) == 0.0

    def test_calculate_cash_on_cash_standard(self):
        coc = calculate_cash_on_cash(annual_cash_flow=12_000_000.0, initial_cash_invested=30_000_000.0)
        assert pytest.approx(coc, rel=1e-5) == 0.40

    def test_calculate_cash_on_cash_zero_capital(self):
        assert calculate_cash_on_cash(annual_cash_flow=5_000_000.0, initial_cash_invested=0.0) == 0.0

    def test_calculate_dscr_standard(self):
        dscr = calculate_dscr(net_operating_income=25_000_000.0, debt_service=20_000_000.0)
        assert dscr is not None
        assert pytest.approx(dscr, rel=1e-5) == 1.25

    def test_calculate_dscr_zero_debt(self):
        assert calculate_dscr(net_operating_income=25_000_000.0, debt_service=0.0) is None


class TestStrategyComparison:
    def test_compare_strategies_default_structure(self):
        rec = compare_strategies(
            landed_cost=40_000_000.0,
            annual_financing_rate=0.20,
            horizon_months=36,
            cash_sale_price=48_000_000.0,
            holding_period_sale=1,
            lease_term=24,
            lease_deposit=10_000_000.0,
            lease_contract_price=58_000_000.0,
            upfront_protection=2_000_000.0,
            monthly_protection=15_000.0,
            exploit_monthly_profit=2_500_000.0,
            exploit_downtime=0.0,
            required_reserve=20_000_000.0,
            batch_step=5,
        )

        assert isinstance(rec, StrategyRecommendation)
        assert rec.recommended_strategy in [StrategyType.CASH_SALE, StrategyType.LEASING, StrategyType.EXPLOITATION]
        assert len(rec.metrics_by_strategy) == 3
        assert StrategyType.CASH_SALE in rec.metrics_by_strategy
        assert StrategyType.LEASING in rec.metrics_by_strategy
        assert StrategyType.EXPLOITATION in rec.metrics_by_strategy

        # Verify comparison table
        assert isinstance(rec.comparison_table, pd.DataFrame)
        assert len(rec.comparison_table) == 3
        required_cols = ["Strategy", "Net Profit", "Gross Margin", "ROI", "NPV", "Risk-Adjusted NPV", "Payback (Months)"]
        for col in required_cols:
            assert col in rec.comparison_table.columns

        # Verify constraints checked
        assert rec.constraints_verified["lease_deposit_above_10m"] is True
        assert rec.constraints_verified["cash_reserve_preserved"] is True
        assert rec.constraints_verified["discrete_batch_rule"] is True

        # Decision rule: recommended strategy has the maximum risk_adjusted_npv
        all_metrics = rec.metrics_by_strategy
        rec_m = all_metrics[rec.recommended_strategy]
        for strat, m in all_metrics.items():
            assert rec_m.risk_adjusted_npv >= m.risk_adjusted_npv

        # Reason text contains details
        assert len(rec.recommendation_reason) > 20
        assert "recommended" in rec.recommendation_reason.lower()

    def test_compare_strategies_cash_sale_wins_when_price_high(self):
        # A massive cash sale price should make Strategy A win
        rec = compare_strategies(
            landed_cost=40_000_000.0,
            annual_financing_rate=0.20,
            horizon_months=36,
            cash_sale_price=80_000_000.0,  # 80M cash sale
            lease_contract_price=50_000_000.0,
            exploit_monthly_profit=1_500_000.0,
        )
        assert rec.recommended_strategy == StrategyType.CASH_SALE
        assert "Strategy A" in rec.recommendation_reason

    def test_compare_strategies_leasing_wins_when_lease_price_high(self):
        # A very high lease contract price should make Strategy B win
        rec = compare_strategies(
            landed_cost=40_000_000.0,
            annual_financing_rate=0.20,
            horizon_months=36,
            cash_sale_price=42_000_000.0,
            lease_contract_price=75_000_000.0,  # 75M lease price
            exploit_monthly_profit=1_500_000.0,
        )
        assert rec.recommended_strategy == StrategyType.LEASING
        assert "Strategy B" in rec.recommendation_reason

    def test_compare_strategies_exploitation_wins_when_profit_high(self):
        # A high monthly exploitation profit should make Strategy C win
        rec = compare_strategies(
            landed_cost=40_000_000.0,
            annual_financing_rate=0.20,
            horizon_months=36,
            cash_sale_price=44_000_000.0,
            lease_contract_price=50_000_000.0,
            exploit_monthly_profit=4_000_000.0,  # 4M/mo net profit
            exploit_downtime=0.0,
        )
        assert rec.recommended_strategy == StrategyType.EXPLOITATION
        assert "Strategy C" in rec.recommendation_reason

    def test_compare_strategies_deposit_under_10m_rejected(self):
        with pytest.raises(SimulatorValidationError):
            compare_strategies(
                landed_cost=40_000_000.0,
                lease_deposit=8_000_000.0,  # Under 10M
            )
