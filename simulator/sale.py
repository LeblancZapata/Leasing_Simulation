"""Cash-sale pricing and return engine."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional, List, Dict, Sequence
import pandas as pd

from simulator.primitives import (
    annual_to_monthly_rate,
    validate_positive_number,
    validate_rate,
    SimulatorValidationError,
)
from simulator.models import CashSaleAssumptions

MARKET_BENCHMARK_PRICES: List[float] = [
    46_000_000.0,
    47_000_000.0,
    48_000_000.0,
    49_000_000.0,
    50_000_000.0,
]


@dataclass
class CashSalePricingResult:
    """Pricing thresholds and configuration for cash sale strategy."""
    landed_cost: float
    target_markup: float
    holding_period_months: int
    acquisition_costs: float
    financing_carry: float
    selling_costs: float
    transaction_costs: float
    risk_reserve: float
    minimum_profit: float
    price_floor: float
    recommended_price: float


@dataclass
class CashSaleEconomics:
    """Financial returns and metrics for a specific cash sale transaction price."""
    sale_price: float
    capital_tied_up: float
    gross_profit: float
    gross_margin: float
    net_profit: float
    net_margin: float
    holding_period_return: float
    annualized_return: float
    capital_released: float
    is_above_floor: bool
    price_floor_delta: float
    holding_period_months: int


def calculate_financing_carry(
    capital_invested: float,
    annual_financing_rate: float,
    holding_period_months: int,
) -> float:
    """Calculate the debt carrying cost of capital tied up during holding period.
    
    Formula:
        monthly_rate = annual_financing_rate / 12
        financing_carry = capital_invested * monthly_rate * holding_period_months
    """
    validate_positive_number("Capital invested", capital_invested, allow_zero=True)
    validate_rate("Annual financing rate", annual_financing_rate, min_rate=0.0, max_rate=1.0)
    if holding_period_months < 0:
        raise SimulatorValidationError("Holding period cannot be negative")

    if holding_period_months == 0 or capital_invested == 0.0 or annual_financing_rate == 0.0:
        return 0.0

    r = annual_to_monthly_rate(annual_financing_rate)
    return capital_invested * r * float(holding_period_months)


def calculate_price_floor(
    landed_cost: float,
    acquisition_costs: float = 0.0,
    financing_carry: float = 0.0,
    selling_costs: float = 0.0,
    risk_reserve: float = 0.0,
    minimum_profit: float = 0.0,
) -> float:
    """Calculate the minimum price acceptable without loss or margin erosion.
    
    Formula:
        price_floor = landed_cost + acquisition_costs + financing_carry + selling_costs + risk_reserve + minimum_profit
    """
    validate_positive_number("Landed cost", landed_cost, allow_zero=False)
    validate_positive_number("Acquisition costs", acquisition_costs, allow_zero=True)
    validate_positive_number("Financing carry", financing_carry, allow_zero=True)
    validate_positive_number("Selling costs", selling_costs, allow_zero=True)
    validate_positive_number("Risk reserve", risk_reserve, allow_zero=True)
    validate_positive_number("Minimum profit", minimum_profit, allow_zero=True)

    return (
        landed_cost
        + acquisition_costs
        + financing_carry
        + selling_costs
        + risk_reserve
        + minimum_profit
    )


def calculate_recommended_price(
    landed_cost: float,
    target_markup: float = 0.20,
    financing_carry: float = 0.0,
    transaction_costs: float = 0.0,
    risk_reserve: float = 0.0,
) -> float:
    """Calculate the recommended asking price based on target markup and carrying costs.
    
    Formula:
        recommended_price = landed_cost * (1 + target_markup) + financing_carry + transaction_costs + risk_reserve
    """
    validate_positive_number("Landed cost", landed_cost, allow_zero=False)
    validate_rate("Target markup", target_markup, min_rate=0.0, max_rate=2.0)
    validate_positive_number("Financing carry", financing_carry, allow_zero=True)
    validate_positive_number("Transaction costs", transaction_costs, allow_zero=True)
    validate_positive_number("Risk reserve", risk_reserve, allow_zero=True)

    return (
        landed_cost * (1.0 + target_markup)
        + financing_carry
        + transaction_costs
        + risk_reserve
    )


def evaluate_cash_sale_pricing(
    landed_cost: float,
    target_markup: float = 0.20,
    holding_period_months: int = 1,
    annual_financing_rate: float = 0.20,
    acquisition_costs: float = 0.0,
    selling_costs: float = 0.0,
    transaction_costs: float = 0.0,
    risk_reserve: float = 0.0,
    minimum_profit: float = 0.0,
    explicit_financing_carry: Optional[float] = None,
) -> CashSalePricingResult:
    """Evaluate comprehensive pricing thresholds for a truck cash sale."""
    validate_positive_number("Landed cost", landed_cost, allow_zero=False)
    validate_rate("Target markup", target_markup, min_rate=0.0, max_rate=2.0)
    if holding_period_months < 0:
        raise SimulatorValidationError("Holding period cannot be negative")

    capital_tied_up = landed_cost + acquisition_costs
    if explicit_financing_carry is not None:
        carry = validate_positive_number("Explicit financing carry", explicit_financing_carry, allow_zero=True)
    else:
        carry = calculate_financing_carry(capital_tied_up, annual_financing_rate, holding_period_months)

    floor_val = calculate_price_floor(
        landed_cost=landed_cost,
        acquisition_costs=acquisition_costs,
        financing_carry=carry,
        selling_costs=selling_costs,
        risk_reserve=risk_reserve,
        minimum_profit=minimum_profit,
    )

    rec_val = calculate_recommended_price(
        landed_cost=landed_cost,
        target_markup=target_markup,
        financing_carry=carry,
        transaction_costs=transaction_costs,
        risk_reserve=risk_reserve,
    )

    return CashSalePricingResult(
        landed_cost=landed_cost,
        target_markup=target_markup,
        holding_period_months=holding_period_months,
        acquisition_costs=acquisition_costs,
        financing_carry=carry,
        selling_costs=selling_costs,
        transaction_costs=transaction_costs,
        risk_reserve=risk_reserve,
        minimum_profit=minimum_profit,
        price_floor=floor_val,
        recommended_price=rec_val,
    )


def evaluate_sale_price_economics(
    sale_price: float,
    pricing: CashSalePricingResult,
) -> CashSaleEconomics:
    """Calculate detailed financial returns (gross/net margins, HPR, annualized return) for a given sale price."""
    validate_positive_number("Sale price", sale_price, allow_zero=False)

    capital_tied_up = pricing.landed_cost + pricing.acquisition_costs
    gross_profit = sale_price - capital_tied_up
    gross_margin = gross_profit / sale_price if sale_price > 0 else 0.0

    # Total costs deducted for net profit: capital tied up + financing carry + selling/transaction costs
    total_costs = capital_tied_up + pricing.financing_carry + pricing.selling_costs + pricing.transaction_costs
    net_profit = sale_price - total_costs
    net_margin = net_profit / sale_price if sale_price > 0 else 0.0

    holding_period_return = net_profit / capital_tied_up if capital_tied_up > 0 else 0.0

    if pricing.holding_period_months > 0:
        # Compound annualization: (1 + HPR)^(12 / n) - 1
        if holding_period_return > -1.0:
            annualized_return = math.pow(1.0 + holding_period_return, 12.0 / pricing.holding_period_months) - 1.0
        else:
            annualized_return = -1.0
    else:
        # Instantaneous sale: annualized return matches nominal annualized multiplier or base HPR
        annualized_return = holding_period_return * 12.0

    is_above_floor = sale_price >= pricing.price_floor
    price_floor_delta = sale_price - pricing.price_floor

    return CashSaleEconomics(
        sale_price=sale_price,
        capital_tied_up=capital_tied_up,
        gross_profit=gross_profit,
        gross_margin=gross_margin,
        net_profit=net_profit,
        net_margin=net_margin,
        holding_period_return=holding_period_return,
        annualized_return=annualized_return,
        capital_released=sale_price,
        is_above_floor=is_above_floor,
        price_floor_delta=price_floor_delta,
        holding_period_months=pricing.holding_period_months,
    )


def generate_market_comparison_table(
    pricing: CashSalePricingResult,
    benchmark_prices: Optional[Sequence[float]] = None,
) -> pd.DataFrame:
    """Generate comparative matrix of economic returns across market benchmark prices (46M, 47M, 48M, etc.)."""
    if benchmark_prices is None:
        benchmark_prices = MARKET_BENCHMARK_PRICES

    rows = []
    for price in benchmark_prices:
        econ = evaluate_sale_price_economics(price, pricing)
        rows.append(
            {
                "Offer Price": econ.sale_price,
                "Gross Profit": econ.gross_profit,
                "Gross Margin": econ.gross_margin,
                "Net Profit": econ.net_profit,
                "Net Margin": econ.net_margin,
                "Holding Period Return": econ.holding_period_return,
                "Annualized Return": econ.annualized_return,
                "Meets Floor?": econ.is_above_floor,
                "Margin vs Floor": econ.price_floor_delta,
            }
        )
    return pd.DataFrame(rows)
