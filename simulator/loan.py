"""Loan amortization calculation engine."""
from __future__ import annotations
import math
from typing import List, Optional
import pandas as pd

from simulator.primitives import (
    annual_to_monthly_rate,
    validate_positive_number,
    validate_rate,
    SimulatorValidationError,
)
from simulator.models import (
    FinancingAssumptions,
    AmortizationRow,
    AmortizationSchedule,
)


def calculate_monthly_payment(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> float:
    """Calculate the constant monthly payment for an amortizing loan.
    
    Formula:
        r = annual_rate / 12
        payment = P * r * (1 + r)^n / ((1 + r)^n - 1)
        
    Special cases:
        - If principal == 0: returns 0.0
        - If annual_rate == 0: returns principal / term_months
    """
    validate_positive_number("Principal", principal, allow_zero=True)
    validate_rate("Annual rate", annual_rate, min_rate=0.0, max_rate=1.0)
    if term_months <= 0:
        raise SimulatorValidationError(f"Loan term must be positive, got {term_months}")

    if principal == 0.0:
        return 0.0

    if annual_rate == 0.0:
        return principal / float(term_months)

    r = annual_to_monthly_rate(annual_rate)
    factor = math.pow(1.0 + r, term_months)
    return principal * r * factor / (factor - 1.0)


def generate_amortization_schedule(
    principal: float,
    annual_rate: float,
    term_months: int,
) -> AmortizationSchedule:
    """Generate the full monthly loan amortization schedule.
    
    Returns an AmortizationSchedule object containing monthly rows:
        month, opening_balance, payment, interest, principal, closing_balance.
    Guarantees:
        - The closing balance at term_months is 0.0.
        - The sum of principal payments exactly equals initial principal.
    """
    validate_positive_number("Principal", principal, allow_zero=True)
    validate_rate("Annual rate", annual_rate, min_rate=0.0, max_rate=1.0)
    if term_months <= 0:
        raise SimulatorValidationError(f"Loan term must be positive, got {term_months}")

    if principal == 0.0:
        return AmortizationSchedule(
            rows=[],
            total_payment=0.0,
            total_interest=0.0,
            total_principal=0.0,
            monthly_payment=0.0,
        )

    monthly_payment = calculate_monthly_payment(principal, annual_rate, term_months)
    r = annual_to_monthly_rate(annual_rate) if annual_rate > 0.0 else 0.0

    rows: List[AmortizationRow] = []
    current_balance = float(principal)

    for m in range(1, term_months + 1):
        opening_balance = current_balance
        interest = opening_balance * r if annual_rate > 0.0 else 0.0

        if m == term_months:
            # Final month adjustment to eliminate precision dust and ensure exact 0.0 balance
            principal_paid = opening_balance
            payment = principal_paid + interest
            closing_balance = 0.0
        else:
            principal_paid = monthly_payment - interest
            closing_balance = max(0.0, opening_balance - principal_paid)
            payment = monthly_payment

        rows.append(
            AmortizationRow(
                month=m,
                opening_balance=opening_balance,
                payment=payment,
                interest=interest,
                principal=principal_paid,
                closing_balance=closing_balance,
            )
        )
        current_balance = closing_balance

    total_payment = sum(row.payment for row in rows)
    total_interest = sum(row.interest for row in rows)
    total_principal = sum(row.principal for row in rows)

    return AmortizationSchedule(
        rows=rows,
        total_payment=total_payment,
        total_interest=total_interest,
        total_principal=total_principal,
        monthly_payment=monthly_payment,
    )


def generate_loan_schedule_from_assumptions(
    assumptions: FinancingAssumptions,
) -> AmortizationSchedule:
    """Convenience helper to generate schedule directly from FinancingAssumptions."""
    return generate_amortization_schedule(
        principal=assumptions.bank_loan_amount,
        annual_rate=assumptions.annual_financing_rate,
        term_months=assumptions.loan_term_months,
    )


def schedule_to_dataframe(schedule: AmortizationSchedule) -> pd.DataFrame:
    """Convert an AmortizationSchedule into a Pandas DataFrame."""
    if not schedule.rows:
        return pd.DataFrame(
            columns=["Month", "Opening Balance", "Payment", "Interest", "Principal", "Closing Balance"]
        )

    data = [
        {
            "Month": row.month,
            "Opening Balance": row.opening_balance,
            "Payment": row.payment,
            "Interest": row.interest,
            "Principal": row.principal,
            "Closing Balance": row.closing_balance,
        }
        for row in schedule.rows
    ]
    return pd.DataFrame(data)
