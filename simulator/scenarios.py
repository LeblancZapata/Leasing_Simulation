"""Multi-scenario matrix runner and sensitivity analysis (Section 13 & Step 12).

Scenario Matrix:
    Landed Cost: 38M (Best), 40M (Average), 42M (Worst)
    Financing Rate: 15%, 20%, 25%
    Lease Term: 6, 12, 18, 24 months
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import pandas as pd

from simulator.primitives import (
    format_fcfa,
    format_pct,
    validate_positive_number,
    validate_rate,
)
from simulator.loan import calculate_monthly_payment
from simulator.sale import evaluate_cash_sale_pricing
from simulator.lease import calculate_dynamic_recommended_lease_price, calculate_lease_price_first
from simulator.metrics import compare_strategies
from simulator.portfolio import StrategyType


DEFAULT_SCENARIO_COSTS = {
    "Best": 38_000_000.0,
    "Average": 40_000_000.0,
    "Worst": 42_000_000.0,
}

DEFAULT_SCENARIO_RATES = [0.15, 0.20, 0.25]
DEFAULT_SCENARIO_TERMS = [6, 12, 18, 24]


@dataclass
class ScenarioResultRow:
    """A single evaluation row in the 36-scenario matrix."""
    cost_label: str
    truck_cost: float
    financing_rate: float
    lease_term: int
    monthly_debt_service_500m: float
    sale_recommended_price: float
    sale_price_floor: float
    lease_recommended_price: float
    lease_monthly_installment: float
    recommended_strategy: str
    best_risk_adj_npv: float
    sale_npv: float
    lease_npv: float
    exploit_npv: float


def run_scenario_matrix(
    truck_costs: Optional[Dict[str, float]] = None,
    financing_rates: Optional[List[float]] = None,
    lease_terms: Optional[List[int]] = None,
    loan_amount: float = 500_000_000.0,
    loan_term_months: int = 36,
    lease_deposit: float = 10_000_000.0,
    exploit_monthly_profit: float = 2_500_000.0,
    exploit_downtime: float = 0.0,
    required_reserve: float = 20_000_000.0,
    upfront_protection: float = 2_000_000.0,
    monthly_protection: float = 15_000.0,
) -> pd.DataFrame:
    """Execute the full 3x3x4 (36 combination) scenario matrix.
    
    Dimensions:
        - 3 truck landed costs: 38M (Best), 40M (Average), 42M (Worst)
        - 3 interest rates: 15%, 20%, 25%
        - 4 lease terms: 6, 12, 18, 24 months
    """
    costs = truck_costs or DEFAULT_SCENARIO_COSTS
    rates = financing_rates or DEFAULT_SCENARIO_RATES
    terms = lease_terms or DEFAULT_SCENARIO_TERMS

    rows: List[Dict[str, Any]] = []

    for cost_label, cost_val in costs.items():
        validate_positive_number(f"Truck cost ({cost_label})", cost_val, allow_zero=False)
        for rate in rates:
            validate_rate(f"Financing rate", rate, min_rate=0.0, max_rate=1.0)
            
            # Debt service on benchmark loan (500M)
            monthly_debt = calculate_monthly_payment(loan_amount, rate, loan_term_months)

            # Cash sale pricing
            sale_pricing = evaluate_cash_sale_pricing(
                landed_cost=cost_val,
                target_markup=0.20,
                holding_period_months=1,
                annual_financing_rate=rate,
            )

            for term in terms:
                # Dynamic lease recommended price
                rec_lease_price = calculate_dynamic_recommended_lease_price(
                    truck_cost=cost_val,
                    initial_deposit=lease_deposit,
                    term_months=term,
                    target_annual_return=0.25,
                    upfront_protection_costs=upfront_protection,
                    monthly_costs=monthly_protection,
                )
                
                # Monthly installment for customer
                lease_eval = calculate_lease_price_first(
                    total_contract_price=rec_lease_price,
                    initial_deposit=lease_deposit,
                    term_months=term,
                    truck_cost=cost_val,
                    upfront_protection_costs=upfront_protection,
                    monthly_costs=monthly_protection,
                    discount_rate=rate,
                )

                # Strategy comparison
                strat_rec = compare_strategies(
                    landed_cost=cost_val,
                    annual_financing_rate=rate,
                    horizon_months=loan_term_months,
                    cash_sale_price=sale_pricing.recommended_price,
                    holding_period_sale=1,
                    lease_term=term,
                    lease_deposit=lease_deposit,
                    lease_contract_price=rec_lease_price,
                    upfront_protection=upfront_protection,
                    monthly_protection=monthly_protection,
                    exploit_monthly_profit=exploit_monthly_profit,
                    exploit_downtime=exploit_downtime,
                    required_reserve=required_reserve,
                )

                best_m = strat_rec.metrics_by_strategy[strat_rec.recommended_strategy]

                rows.append({
                    "Scenario Cost": f"{cost_label} ({cost_val / 1e6:.0f}M)",
                    "Truck Cost (FCFA)": cost_val,
                    "Financing Rate": rate,
                    "Lease Term (Mos)": term,
                    "Monthly Debt Service (500M)": monthly_debt,
                    "Sale Rec Price": sale_pricing.recommended_price,
                    "Sale Price Floor": sale_pricing.price_floor,
                    "Lease Rec Price": rec_lease_price,
                    "Lease Monthly Installment": lease_eval.monthly_installment,
                    "Recommended Strategy": strat_rec.recommended_strategy.value,
                    "Best Risk-Adjusted NPV": best_m.risk_adjusted_npv,
                    "Sale NPV": strat_rec.metrics_by_strategy[StrategyType.CASH_SALE].npv,
                    "Lease NPV": strat_rec.metrics_by_strategy[StrategyType.LEASING].npv,
                    "Exploit NPV": strat_rec.metrics_by_strategy[StrategyType.EXPLOITATION].npv,
                })

    return pd.DataFrame(rows)


def run_preset_comparison(
    rate: float = 0.20,
    term: int = 24,
    loan_amount: float = 500_000_000.0,
    loan_term_months: int = 36,
    lease_deposit: float = 10_000_000.0,
    exploit_monthly_profit: float = 2_500_000.0,
    downtime: float = 0.0,
) -> pd.DataFrame:
    """Compare Best (38M), Average (40M), and Worst (42M) scenarios for fixed rate & term."""
    df_matrix = run_scenario_matrix(
        financing_rates=[rate],
        lease_terms=[term],
        loan_amount=loan_amount,
        loan_term_months=loan_term_months,
        lease_deposit=lease_deposit,
        exploit_monthly_profit=exploit_monthly_profit,
        exploit_downtime=downtime,
    )
    return df_matrix

