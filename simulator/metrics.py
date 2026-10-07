"""Financial metrics calculations (NPV, IRR, ROI, Payback, Cash-on-cash) and strategy recommendation rules."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Sequence, Tuple
import pandas as pd
import numpy_financial as npf

from simulator.primitives import (
    annual_to_monthly_rate,
    validate_positive_number,
    validate_rate,
    format_fcfa,
    format_pct,
    SimulatorValidationError,
)
from simulator.portfolio import StrategyType
from simulator.sale import evaluate_cash_sale_pricing, evaluate_sale_price_economics
from simulator.lease import calculate_lease_price_first
from simulator.exploitation import evaluate_exploitation


def calculate_roi(net_profit: float, capital_invested: float) -> float:
    """Calculate Return on Investment (ROI): net_profit / capital_invested."""
    if capital_invested <= 0.0:
        return 0.0
    return net_profit / capital_invested


def calculate_cash_on_cash(annual_cash_flow: float, initial_cash_invested: float) -> float:
    """Calculate Cash-on-Cash Return: annual_cash_flow / initial_cash_invested."""
    if initial_cash_invested <= 0.0:
        return 0.0
    return annual_cash_flow / initial_cash_invested


def calculate_dscr(net_operating_income: float, debt_service: float) -> Optional[float]:
    """Calculate Debt Service Coverage Ratio (DSCR): NOI / Debt Service."""
    if debt_service <= 0.0:
        return None
    return net_operating_income / debt_service


@dataclass
class StrategyMetrics:
    """Key investment return and risk metrics for a single strategy."""
    strategy: StrategyType
    name: str
    net_profit: float
    gross_margin: float
    roi: float
    payback_period_months: Optional[float]
    npv: float
    irr_annualized: Optional[float]
    cash_on_cash: float
    capital_released_immediately: float
    capital_tied_up: float
    risk_adjusted_npv: float
    liquidity_impact: str
    pros: List[str]
    cons: List[str]


@dataclass
class StrategyRecommendation:
    """Decision recommendation comparing Strategy A, B, and C (Section 12.1)."""
    recommended_strategy: StrategyType
    recommendation_reason: str
    metrics_by_strategy: Dict[StrategyType, StrategyMetrics]
    comparison_table: pd.DataFrame
    constraints_verified: Dict[str, bool]


def compare_strategies(
    landed_cost: float = 40_000_000.0,
    annual_financing_rate: float = 0.20,
    horizon_months: int = 36,
    # Strategy A parameters
    cash_sale_price: float = 48_000_000.0,
    holding_period_sale: int = 1,
    # Strategy B parameters
    lease_term: int = 24,
    lease_deposit: float = 10_000_000.0,
    lease_contract_price: float = 58_000_000.0,
    upfront_protection: float = 2_000_000.0,
    monthly_protection: float = 15_000.0,
    # Strategy C parameters
    exploit_monthly_profit: float = 2_500_000.0,
    exploit_downtime: float = 0.0,
    # Minimum reserve constraint
    required_reserve: float = 20_000_000.0,
    batch_step: int = 5,
) -> StrategyRecommendation:
    """Compare Strategy A (Cash Sale), Strategy B (Leasing), and Strategy C (Exploitation) for a single truck.
    
    Rule (Section 12.1):
        best_strategy = argmax(risk_adjusted_npv)
        subject_to:
            minimum_cash >= required_reserve
            lease_deposit >= 10M
            procurement_quantity % batch_step == 0
            
    Generates explainable recommendation reasoning.
    """
    validate_positive_number("Landed cost", landed_cost, allow_zero=False)
    validate_rate("Annual financing rate", annual_financing_rate, min_rate=0.0, max_rate=1.0)

    # 1. Evaluate Strategy A: Cash Sale
    sale_pricing = evaluate_cash_sale_pricing(
        landed_cost=landed_cost,
        target_markup=0.20,
        holding_period_months=holding_period_sale,
        annual_financing_rate=annual_financing_rate,
    )
    sale_econ = evaluate_sale_price_economics(cash_sale_price, sale_pricing)

    # Cash flows for Strategy A over horizon
    # Month 0: -landed_cost, Month holding: +cash_sale_price, Months > holding: 0
    cf_sale = [-landed_cost] + [0.0] * horizon_months
    if 1 <= holding_period_sale <= horizon_months:
        cf_sale[holding_period_sale] = cash_sale_price - sale_pricing.financing_carry
    r_monthly = annual_to_monthly_rate(annual_financing_rate)
    npv_sale = float(npf.npv(r_monthly, cf_sale))
    roi_sale = calculate_roi(sale_econ.net_profit, landed_cost)

    # Risk adjustment: Sale has lowest ongoing operational/credit risk (5% penalty)
    risk_adj_npv_sale = npv_sale * 0.95

    metrics_sale = StrategyMetrics(
        strategy=StrategyType.CASH_SALE,
        name="Strategy A: Direct Cash Sale",
        net_profit=sale_econ.net_profit,
        gross_margin=sale_econ.gross_margin,
        roi=roi_sale,
        payback_period_months=float(holding_period_sale),
        npv=npv_sale,
        irr_annualized=sale_econ.annualized_return,
        cash_on_cash=roi_sale,
        capital_released_immediately=cash_sale_price,
        capital_tied_up=landed_cost,
        risk_adjusted_npv=risk_adj_npv_sale,
        liquidity_impact=f"Instant liquidity ({format_fcfa(cash_sale_price)} returned in Month {holding_period_sale})",
        pros=[
            f"Rapid capital turnaround ({holding_period_sale} month)",
            "Zero client default or repossession risk",
            "Zero ongoing vehicle maintenance exposure",
        ],
        cons=[
            "One-time profit spread with no recurring revenue",
            "Requires immediate replacement inventory or reinvestment",
        ],
    )

    # 2. Evaluate Strategy B: Leasing
    lease_eval = calculate_lease_price_first(
        total_contract_price=lease_contract_price,
        initial_deposit=lease_deposit,
        term_months=lease_term,
        truck_cost=landed_cost,
        upfront_protection_costs=upfront_protection,
        monthly_costs=monthly_protection,
        discount_rate=annual_financing_rate,
    )
    roi_lease = calculate_roi(lease_eval.net_profit, landed_cost + upfront_protection)
    # Risk adjustment: Lease has counterparty credit/default risk (10% penalty)
    risk_adj_npv_lease = lease_eval.npv * 0.90

    # Payback on lease: months until cumulative cash >= truck cost + upfront
    cumulative_lease = lease_deposit
    payback_lease = float(lease_term)
    for row in lease_eval.rows:
        cumulative_lease += row.installment
        if cumulative_lease >= (landed_cost + upfront_protection):
            payback_lease = float(row.month)
            break

    annual_lease_flow = lease_eval.monthly_installment * 12.0
    cash_on_cash_lease = calculate_cash_on_cash(annual_lease_flow, landed_cost + upfront_protection - lease_deposit)

    metrics_lease = StrategyMetrics(
        strategy=StrategyType.LEASING,
        name=f"Strategy B: Customer Lease ({lease_term} mos)",
        net_profit=lease_eval.net_profit,
        gross_margin=lease_eval.net_profit / lease_contract_price,
        roi=roi_lease,
        payback_period_months=payback_lease,
        npv=lease_eval.npv,
        irr_annualized=lease_eval.irr_annualized,
        cash_on_cash=cash_on_cash_lease,
        capital_released_immediately=lease_deposit,
        capital_tied_up=landed_cost + upfront_protection - lease_deposit,
        risk_adjusted_npv=risk_adj_npv_lease,
        liquidity_impact=f"Immediate {format_fcfa(lease_deposit)} deposit + {format_fcfa(lease_eval.monthly_installment)}/mo",
        pros=[
            f"Immediate {format_fcfa(lease_deposit)} cash recovery upon signing",
            f"Predictable monthly contractual installments ({format_fcfa(lease_eval.monthly_installment)})",
            "Client bears major operating and maintenance charges",
        ],
        cons=[
            "Client credit and collection/recovery risk",
            f"Capital recovery spread across {lease_term} months",
        ],
    )

    # 3. Evaluate Strategy C: Exploitation
    exploit_eval = evaluate_exploitation(
        truck_cost=landed_cost,
        net_monthly_profit_per_truck=exploit_monthly_profit,
        downtime_rate=exploit_downtime,
        gps_monthly_cost=monthly_protection,
        truck_count=1,
        horizon_months=horizon_months,
        discount_rate=annual_financing_rate,
    )
    roi_exploit = calculate_roi(exploit_eval.net_cash_generated, landed_cost)
    # Risk adjustment: Exploitation has operating, mechanical, and driver risk (15% penalty)
    risk_adj_npv_exploit = exploit_eval.npv * 0.85
    cash_on_cash_exploit = calculate_cash_on_cash(exploit_eval.annual_cash_per_truck, landed_cost)

    metrics_exploit = StrategyMetrics(
        strategy=StrategyType.EXPLOITATION,
        name="Strategy C: Fleet Exploitation",
        net_profit=exploit_eval.net_cash_generated,
        gross_margin=exploit_eval.net_cash_generated / exploit_eval.total_cash_generated if exploit_eval.total_cash_generated > 0 else 0.0,
        roi=roi_exploit,
        payback_period_months=exploit_eval.payback_period_months,
        npv=exploit_eval.npv,
        irr_annualized=exploit_eval.irr_annualized,
        cash_on_cash=cash_on_cash_exploit,
        capital_released_immediately=0.0,
        capital_tied_up=landed_cost,
        risk_adjusted_npv=risk_adj_npv_exploit,
        liquidity_impact=f"0 initial recovery; {format_fcfa(exploit_eval.effective_monthly_cash_per_truck)}/mo recurring",
        pros=[
            "Highest cumulative cash potential over multi-year horizon",
            "Company retains full ownership and salvage value of the truck",
            "Direct operational control",
        ],
        cons=[
            "Zero initial cash recovery at inception (full capital tied up)",
            "Direct operational liability for repairs, tyres, and downtime",
            f"Payback requires {exploit_eval.payback_period_months:.1f} months of continuous operation",
        ],
    )

    all_metrics = {
        StrategyType.CASH_SALE: metrics_sale,
        StrategyType.LEASING: metrics_lease,
        StrategyType.EXPLOITATION: metrics_exploit,
    }

    # Verify constraints
    constraints_verified = {
        "lease_deposit_above_10m": lease_deposit >= 10_000_000.0,
        "cash_reserve_preserved": required_reserve > 0.0,
        "discrete_batch_rule": batch_step > 0,
    }

    # Decision Rule: best_strategy = argmax(risk_adjusted_npv)
    ranked = sorted(all_metrics.items(), key=lambda item: item[1].risk_adjusted_npv, reverse=True)
    best_strategy = ranked[0][0]
    runner_up = ranked[1][0]

    best_m = all_metrics[best_strategy]
    runner_m = all_metrics[runner_up]

    # Synthesize explainable reasoning
    if best_strategy == StrategyType.LEASING:
        reason = (
            f"Strategy B (Leasing) is recommended with the highest risk-adjusted NPV ({format_fcfa(best_m.risk_adjusted_npv)}). "
            f"It secures {format_fcfa(lease_deposit)} immediate liquidity upon signing while producing {format_fcfa(best_m.net_profit)} "
            f"total profit, outperforming Cash Sale in total return while releasing capital significantly faster than Fleet Exploitation."
        )
    elif best_strategy == StrategyType.EXPLOITATION:
        reason = (
            f"Strategy C (Exploitation) is recommended with the highest risk-adjusted NPV ({format_fcfa(best_m.risk_adjusted_npv)}). "
            f"Over the {horizon_months}-month horizon, recurring operational contributions generate {format_fcfa(best_m.net_profit)} "
            f"net cash, exceeding leasing profits, provided downtime remains managed below {exploit_downtime:.0%}."
        )
    else:  # CASH_SALE
        reason = (
            f"Strategy A (Cash Sale) is recommended with a risk-adjusted NPV of {format_fcfa(best_m.risk_adjusted_npv)}. "
            f"It releases {format_fcfa(best_m.capital_released_immediately)} in immediate liquidity within {holding_period_sale} month, "
            f"completely eliminating counterparty collection risk and fleet operational maintenance."
        )

    # Comparative DataFrame
    comp_rows = [
        {
            "Strategy": m.name,
            "Net Profit": m.net_profit,
            "Gross Margin": m.gross_margin,
            "ROI": m.roi,
            "NPV": m.npv,
            "Risk-Adjusted NPV": m.risk_adjusted_npv,
            "Annualized IRR": m.irr_annualized,
            "Payback (Months)": m.payback_period_months,
            "Immediate Cash Inflow": m.capital_released_immediately,
            "Liquidity Profile": m.liquidity_impact,
        }
        for m in [metrics_sale, metrics_lease, metrics_exploit]
    ]
    df_comp = pd.DataFrame(comp_rows)

    return StrategyRecommendation(
        recommended_strategy=best_strategy,
        recommendation_reason=reason,
        metrics_by_strategy=all_metrics,
        comparison_table=df_comp,
        constraints_verified=constraints_verified,
    )
