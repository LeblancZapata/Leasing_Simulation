"""Cost structure, protection costs, and operational expense engine."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from simulator.primitives import (
    validate_positive_number,
    validate_rate,
    SimulatorValidationError,
)
from simulator.models import ProtectionCostConfig, ProtectionCostItem


@dataclass
class LeaseProtectionBreakdown:
    """Detailed itemized breakdown of protection and security costs for a leased truck."""
    financed_receivable: float
    term_months: int
    fixed_upfront_total: float
    variable_rate_total: float
    variable_amount: float
    monthly_recurring_total: float
    total_recurring_over_term: float
    total_protection_cost: float
    itemized_records: List[Dict[str, Any]]


def calculate_lease_protection(
    config: ProtectionCostConfig,
    financed_receivable: float,
    term_months: int,
) -> LeaseProtectionBreakdown:
    """Calculate the itemized and total protection cost per leased truck based on enabled items.
    
    Distinguishes:
        - Fixed upfront fees (GPS install, contract drafting, pre-inspection, etc.)
        - Variable reserve rates (applied as % of customer financed receivable, e.g. collection reserve)
        - Monthly recurring fees (GPS tracking subscriptions over the term)
    """
    validate_positive_number("Financed receivable", financed_receivable, allow_zero=True)
    if term_months <= 0:
        raise SimulatorValidationError("Term months must be positive")

    items: List[ProtectionCostItem] = [
        config.gps_installation,
        config.gps_monthly_sub,
        config.contract_preparation,
        config.customer_credit_check,
        config.insurance_upfront,
        config.pre_handover_inspection,
        config.legal_registration,
        config.default_reserve,
        config.repossession_reserve,
        config.legal_enforcement_reserve,
        config.payment_processing_fees,
    ]

    fixed_upfront = 0.0
    variable_rate = 0.0
    monthly_recurring = 0.0
    records: List[Dict[str, Any]] = []

    for item in items:
        if not item.enabled:
            records.append({
                "item": item.name,
                "status": "Disabled",
                "type": "N/A",
                "rate_or_amount": item.amount,
                "effective_cost": 0.0,
                "provenance": "commercial_input_assumption",
            })
            continue

        if item.is_recurring_monthly:
            monthly_recurring += item.amount
            effective_cost = item.amount * float(term_months)
            item_type = "Monthly Recurring"
        elif item.is_percentage:
            variable_rate += item.amount
            effective_cost = financed_receivable * item.amount
            item_type = "% of Financed Balance"
        else:
            fixed_upfront += item.amount
            effective_cost = item.amount
            item_type = "Fixed Upfront"

        records.append({
            "item": item.name,
            "status": "Active",
            "type": item_type,
            "rate_or_amount": item.amount,
            "effective_cost": effective_cost,
            "provenance": "commercial_input_assumption",
        })

    variable_amount = financed_receivable * variable_rate
    total_recurring_over_term = monthly_recurring * float(term_months)
    total_protection_cost = fixed_upfront + variable_amount + total_recurring_over_term

    return LeaseProtectionBreakdown(
        financed_receivable=financed_receivable,
        term_months=term_months,
        fixed_upfront_total=fixed_upfront,
        variable_rate_total=variable_rate,
        variable_amount=variable_amount,
        monthly_recurring_total=monthly_recurring,
        total_recurring_over_term=total_recurring_over_term,
        total_protection_cost=total_protection_cost,
        itemized_records=records,
    )


@dataclass
class FleetOperationalCostConfig:
    """Configurable operating costs for Strategy C (Fleet Exploitation)."""
    maintenance_monthly_per_truck: float = 350_000.0  # Commercial estimate
    tyres_repairs_monthly_reserve: float = 200_000.0  # Commercial estimate
    parking_yard_monthly_reserve: float = 50_000.0    # Commercial estimate
    annual_insurance_per_truck: float = 1_200_000.0   # Commercial estimate
    admin_accounting_monthly_per_truck: float = 50_000.0  # Commercial estimate

    def total_monthly_direct_operating_cost(self) -> float:
        """Total monthly recurring operational cost per truck."""
        monthly_insurance = self.annual_insurance_per_truck / 12.0
        return (
            self.maintenance_monthly_per_truck
            + self.tyres_repairs_monthly_reserve
            + self.parking_yard_monthly_reserve
            + monthly_insurance
            + self.admin_accounting_monthly_per_truck
        )
