"""Leasing and installment financing engine."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
import pandas as pd
import numpy_financial as npf

from simulator.primitives import (
    annual_to_monthly_rate,
    validate_positive_number,
    validate_rate,
    validate_lease_term,
    validate_lease_deposit,
    SimulatorValidationError,
)
from simulator.models import LeaseAssumptions

ALLOWED_LEASE_TERMS: Tuple[int, ...] = (6, 12, 18, 24)
MINIMUM_LEASE_DEPOSIT: float = 10_000_000.0


@dataclass
class LeaseScheduleRow:
    """Monthly record in the customer repayment and receivable schedule."""
    month: int
    opening_receivable: float
    installment: float
    closing_receivable: float
    cumulative_cash_received: float
    net_cash_flow: float


@dataclass
class LeaseEvaluationResult:
    """Comprehensive financial evaluation and repayment schedule for a lease agreement."""
    term_months: int
    initial_deposit: float
    total_contract_price: float
    financed_balance: float
    monthly_installment: float
    total_contractual_receipts: float
    truck_cost: float
    upfront_protection_costs: float
    total_recurring_costs: float
    total_costs: float
    net_profit: float
    break_even_payment: float
    break_even_contract_price: float
    npv: float
    irr_annualized: Optional[float]
    cash_flows: List[float]
    rows: List[LeaseScheduleRow]
    mode_used: str  # "price_first" or "payment_capacity_first"

    @property
    def capital_recovered_by_month(self) -> Dict[int, float]:
        """Month-by-month cumulative customer cash received."""
        result = {0: self.initial_deposit}
        for row in self.rows:
            result[row.month] = row.cumulative_cash_received
        return result

    @property
    def outstanding_receivables_by_month(self) -> Dict[int, float]:
        """Month-by-month outstanding customer balance."""
        result = {0: self.financed_balance}
        for row in self.rows:
            result[row.month] = row.closing_receivable
        return result


def _build_lease_schedule(
    total_contract_price: float,
    initial_deposit: float,
    term_months: int,
    truck_cost: float,
    upfront_protection_costs: float = 0.0,
    monthly_costs: float = 0.0,
    discount_rate: float = 0.20,
    early_payoff_month: Optional[int] = None,
    mode_used: str = "price_first",
) -> LeaseEvaluationResult:
    """Internal builder for complete lease schedule, cash flows, NPV, and IRR."""
    # Validation rules
    validate_lease_term(term_months, allowed_terms=ALLOWED_LEASE_TERMS)
    validate_lease_deposit(initial_deposit, min_deposit=MINIMUM_LEASE_DEPOSIT)
    validate_positive_number("Total contract price", total_contract_price, allow_zero=False)
    validate_positive_number("Truck cost", truck_cost, allow_zero=False)
    validate_positive_number("Upfront protection costs", upfront_protection_costs, allow_zero=True)
    validate_positive_number("Monthly costs", monthly_costs, allow_zero=True)
    validate_rate("Discount rate", discount_rate, min_rate=0.0, max_rate=1.0)

    if total_contract_price < initial_deposit:
        raise SimulatorValidationError(
            f"Total contract price ({total_contract_price:,.0f}) cannot be less than initial deposit ({initial_deposit:,.0f})"
        )

    financed_balance = total_contract_price - initial_deposit
    standard_monthly_installment = financed_balance / float(term_months) if term_months > 0 else 0.0

    # Month 0 Cash Flow: initial deposit received minus acquisition & upfront protection expenditure
    initial_investment = truck_cost + upfront_protection_costs
    cf_0 = initial_deposit - initial_investment
    cash_flows: List[float] = [cf_0]

    rows: List[LeaseScheduleRow] = []
    current_receivable = financed_balance
    cumulative_cash = initial_deposit

    for m in range(1, term_months + 1):
        opening_rec = current_receivable

        if early_payoff_month is not None and m == early_payoff_month:
            # Customer pays remaining balance in full
            inst = opening_rec
            closing_rec = 0.0
        elif early_payoff_month is not None and m > early_payoff_month:
            # Already paid off
            inst = 0.0
            closing_rec = 0.0
        else:
            if m == term_months:
                # Final month exact closure
                inst = opening_rec
                closing_rec = 0.0
            else:
                inst = standard_monthly_installment
                closing_rec = max(0.0, opening_rec - inst)

        cumulative_cash += inst
        net_cf_m = inst - monthly_costs
        cash_flows.append(net_cf_m)

        rows.append(
            LeaseScheduleRow(
                month=m,
                opening_receivable=opening_rec,
                installment=inst,
                closing_receivable=closing_rec,
                cumulative_cash_received=cumulative_cash,
                net_cash_flow=net_cf_m,
            )
        )
        current_receivable = closing_rec

    total_contractual_receipts = initial_deposit + sum(r.installment for r in rows)
    total_recurring_costs = monthly_costs * float(term_months)
    total_costs = truck_cost + upfront_protection_costs + total_recurring_costs
    net_profit = total_contractual_receipts - total_costs

    # Break-even calculations
    break_even_contract_price = total_costs
    break_even_payment = max(0.0, (total_costs - initial_deposit) / float(term_months))

    # NPV Calculation
    r_monthly = annual_to_monthly_rate(discount_rate)
    npv_val = float(npf.npv(r_monthly, cash_flows))

    # IRR Calculation
    try:
        monthly_irr = float(npf.irr(cash_flows))
        if math.isnan(monthly_irr) or math.isinf(monthly_irr):
            annualized_irr = None
        elif monthly_irr > -1.0:
            annualized_irr = math.pow(1.0 + monthly_irr, 12.0) - 1.0
        else:
            annualized_irr = -1.0
    except Exception:
        annualized_irr = None

    return LeaseEvaluationResult(
        term_months=term_months,
        initial_deposit=initial_deposit,
        total_contract_price=total_contract_price,
        financed_balance=financed_balance,
        monthly_installment=standard_monthly_installment,
        total_contractual_receipts=total_contractual_receipts,
        truck_cost=truck_cost,
        upfront_protection_costs=upfront_protection_costs,
        total_recurring_costs=total_recurring_costs,
        total_costs=total_costs,
        net_profit=net_profit,
        break_even_payment=break_even_payment,
        break_even_contract_price=break_even_contract_price,
        npv=npv_val,
        irr_annualized=annualized_irr,
        cash_flows=cash_flows,
        rows=rows,
        mode_used=mode_used,
    )


def calculate_lease_price_first(
    total_contract_price: float,
    initial_deposit: float,
    term_months: int,
    truck_cost: float,
    upfront_protection_costs: float = 0.0,
    monthly_costs: float = 0.0,
    discount_rate: float = 0.20,
    early_payoff_month: Optional[int] = None,
) -> LeaseEvaluationResult:
    """Direction 1: User specifies target contract price + deposit + term.
    
    The program calculates the monthly installment and economic return.
    """
    return _build_lease_schedule(
        total_contract_price=total_contract_price,
        initial_deposit=initial_deposit,
        term_months=term_months,
        truck_cost=truck_cost,
        upfront_protection_costs=upfront_protection_costs,
        monthly_costs=monthly_costs,
        discount_rate=discount_rate,
        early_payoff_month=early_payoff_month,
        mode_used="price_first",
    )


def calculate_lease_payment_first(
    max_monthly_payment: float,
    initial_deposit: float,
    term_months: int,
    truck_cost: float,
    upfront_protection_costs: float = 0.0,
    monthly_costs: float = 0.0,
    discount_rate: float = 0.20,
    early_payoff_month: Optional[int] = None,
) -> LeaseEvaluationResult:
    """Direction 2: User specifies customer maximum monthly payment capacity + deposit + term.
    
    The program derives the resulting total contract price = deposit + (monthly_payment * term_months).
    """
    validate_positive_number("Max monthly payment", max_monthly_payment, allow_zero=False)
    validate_lease_term(term_months, allowed_terms=ALLOWED_LEASE_TERMS)
    validate_lease_deposit(initial_deposit, min_deposit=MINIMUM_LEASE_DEPOSIT)

    total_contract_price = initial_deposit + (max_monthly_payment * float(term_months))

    return _build_lease_schedule(
        total_contract_price=total_contract_price,
        initial_deposit=initial_deposit,
        term_months=term_months,
        truck_cost=truck_cost,
        upfront_protection_costs=upfront_protection_costs,
        monthly_costs=monthly_costs,
        discount_rate=discount_rate,
        early_payoff_month=early_payoff_month,
        mode_used="payment_capacity_first",
    )


def calculate_dynamic_recommended_lease_price(
    truck_cost: float,
    initial_deposit: float,
    term_months: int,
    base_cash_price: Optional[float] = None,
    target_annual_return: float = 0.15,
    commercial_markup: float = 0.15,
    upfront_protection_costs: float = 0.0,
    monthly_costs: float = 0.0,
) -> float:
    """Calculate recommended lease contract price ensuring:
    1. Lease price is strictly greater than the normal cash sale price (base asset value).
    2. Interest charged is dynamic: client with smaller deposit pays more interest than client
       with larger deposit, because they hold more of the company's capital.
    3. Longer timelines accumulate more financing interest than shorter timelines.
    """
    validate_positive_number("Truck cost", truck_cost, allow_zero=False)
    validate_lease_deposit(initial_deposit, min_deposit=MINIMUM_LEASE_DEPOSIT)
    validate_lease_term(term_months, allowed_terms=ALLOWED_LEASE_TERMS)
    validate_rate("Target annual return", target_annual_return, min_rate=0.0, max_rate=2.0)

    # Base commercial cash asset price
    if base_cash_price is not None and base_cash_price > 0:
        base_price = base_cash_price + upfront_protection_costs
    else:
        base_price = (truck_cost * (1.0 + commercial_markup)) + upfront_protection_costs

    # Remaining principal of company money financed for the client
    financed_balance = max(0.0, base_price - initial_deposit)

    if financed_balance <= 0.0:
        return max(base_price, initial_deposit) + (monthly_costs * float(term_months))

    # Amortization monthly rate
    r_monthly = target_annual_return / 12.0
    if r_monthly > 0 and term_months > 0:
        factor = math.pow(1.0 + r_monthly, term_months)
        installment_principal_interest = financed_balance * (r_monthly * factor) / (factor - 1.0)
    else:
        installment_principal_interest = financed_balance / float(term_months)

    total_contract_price = initial_deposit + (installment_principal_interest + monthly_costs) * float(term_months)
    return round(total_contract_price, 2)


def lease_schedule_to_dataframe(result: LeaseEvaluationResult) -> pd.DataFrame:
    """Convert lease evaluation rows into a Pandas DataFrame."""
    data = [
        {
            "Month": row.month,
            "Opening Receivable": row.opening_receivable,
            "Installment": row.installment,
            "Closing Receivable": row.closing_receivable,
            "Cumulative Recovered": row.cumulative_cash_received,
            "Net Cash Flow": row.net_cash_flow,
        }
        for row in result.rows
    ]
    return pd.DataFrame(data)


@dataclass
class ClientLeaseOption:
    """A structured lease option presented to a client for a specific term."""
    term_months: int
    is_offered: bool
    rejection_reason: Optional[str]
    initial_deposit: float
    financed_balance: float
    total_contract_price: float
    monthly_installment: float
    company_net_profit: float
    profit_margin: float
    payback_month: int
    is_recommended: bool
    base_cash_price: float = 0.0
    total_interest_paid: float = 0.0
    evaluation: Optional[LeaseEvaluationResult] = None


def generate_client_lease_options(
    truck_cost: float,
    initial_deposit: float,
    base_cash_price: Optional[float] = None,
    upfront_protection_costs: float = 0.0,
    monthly_costs: float = 0.0,
    target_annual_return: float = 0.15,
    commercial_markup: float = 0.15,
    discount_rate: float = 0.15,
) -> List[ClientLeaseOption]:
    """Generate tailored leasing possibilities for a client based on their down payment.
    
    Core Business Rules:
    - Duration cannot exceed 2 years (max 24 months). Options are 6, 12, 18, 24 months.
    - Initial deposit must be >= 10M FCFA.
    - Total lease price is strictly > normal cash sale price (base asset value).
    - Client with 10M deposit pays MORE interest than client with 30M deposit.
    - Company net margin is higher for smaller deposits due to greater financing interest.
    - If deposit is >= 28M FCFA, 18-month and 24-month options are NOT offered.
    """
    options: List[ClientLeaseOption] = []
    terms = [6, 12, 18, 24]

    actual_base_price = (
        (base_cash_price if base_cash_price is not None and base_cash_price > 0 else (truck_cost * (1.0 + commercial_markup)))
        + upfront_protection_costs
    )

    if initial_deposit < MINIMUM_LEASE_DEPOSIT:
        for t_mo in terms:
            options.append(
                ClientLeaseOption(
                    term_months=t_mo,
                    is_offered=False,
                    rejection_reason=f"Acompte insuffisant ({initial_deposit:,.0f} FCFA). L'apport minimum légal requis est de 10 000 000 FCFA.",
                    initial_deposit=initial_deposit,
                    financed_balance=0.0,
                    total_contract_price=0.0,
                    monthly_installment=0.0,
                    company_net_profit=0.0,
                    profit_margin=0.0,
                    payback_month=0,
                    is_recommended=False,
                    base_cash_price=actual_base_price,
                    total_interest_paid=0.0,
                )
            )
        return options

    for t_mo in terms:
        rec_price = calculate_dynamic_recommended_lease_price(
            truck_cost=truck_cost,
            initial_deposit=initial_deposit,
            term_months=t_mo,
            base_cash_price=base_cash_price,
            target_annual_return=target_annual_return,
            commercial_markup=commercial_markup,
            upfront_protection_costs=upfront_protection_costs,
            monthly_costs=monthly_costs,
        )

        eval_res = calculate_lease_price_first(
            total_contract_price=rec_price,
            initial_deposit=initial_deposit,
            term_months=t_mo,
            truck_cost=truck_cost,
            upfront_protection_costs=upfront_protection_costs,
            monthly_costs=monthly_costs,
            discount_rate=discount_rate,
        )

        total_interest = max(0.0, eval_res.total_contract_price - actual_base_price - (monthly_costs * float(t_mo)))

        # Payback calculation: when cumulative cash >= truck cost + upfront
        total_investment = truck_cost + upfront_protection_costs
        payback_m = t_mo
        cum_cash = initial_deposit
        for row in eval_res.rows:
            cum_cash += row.installment
            if cum_cash >= total_investment:
                payback_m = row.month
                break

        # Eligibility logic based on initial deposit
        is_offered = True
        rejection_reason = None
        is_rec = False

        if initial_deposit >= 28_000_000.0:
            if t_mo in (18, 24):
                is_offered = False
                rejection_reason = f"Non proposé : avec un acompte de {initial_deposit/1e6:.0f}M FCFA, le reliquat est très faible. Financer ce petit solde sur {t_mo} mois bloquerait le capital de l'entreprise pour des mensualités dérisoires."
            elif t_mo == 6:
                is_rec = True
            elif t_mo == 12:
                is_rec = False
        elif initial_deposit >= 22_000_000.0:
            if t_mo == 24:
                is_offered = False
                rejection_reason = f"Non proposé : avec un acompte de {initial_deposit/1e6:.0f}M FCFA, la durée maximale conseillée est de 18 mois."
            elif t_mo == 12:
                is_rec = True
        else:  # 10M - 21M deposit
            if t_mo == 6 and eval_res.monthly_installment > 5_000_000.0:
                is_rec = False
            elif t_mo == 24 and initial_deposit <= 15_000_000.0:
                is_rec = True
            elif t_mo == 18 and initial_deposit > 15_000_000.0:
                is_rec = True

        options.append(
            ClientLeaseOption(
                term_months=t_mo,
                is_offered=is_offered,
                rejection_reason=rejection_reason,
                initial_deposit=initial_deposit,
                financed_balance=eval_res.financed_balance,
                total_contract_price=eval_res.total_contract_price,
                monthly_installment=eval_res.monthly_installment,
                company_net_profit=eval_res.net_profit,
                profit_margin=eval_res.net_profit / eval_res.total_contract_price if eval_res.total_contract_price > 0 else 0.0,
                payback_month=payback_m,
                is_recommended=is_rec,
                base_cash_price=actual_base_price,
                total_interest_paid=total_interest,
                evaluation=eval_res,
            )
        )

    return options
