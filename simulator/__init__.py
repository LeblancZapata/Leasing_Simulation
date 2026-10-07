"""Dump Truck Finance & Leasing Simulator package."""

__version__ = "1.0.0"

from simulator.primitives import (
    SimulatorValidationError,
    round_currency,
    format_fcfa,
    parse_fcfa,
    annual_to_monthly_rate,
    monthly_to_annual_rate,
    format_pct,
    month_to_calendar,
    format_month_label,
    validate_positive_number,
    validate_rate,
    validate_lease_term,
    validate_lease_deposit,
    validate_batch_step,
)

from simulator.models import (
    FinancingAssumptions,
    ProcurementAssumptions,
    CashSaleAssumptions,
    LeaseAssumptions,
    ExploitationAssumptions,
    ProtectionCostConfig,
    ProtectionCostItem,
    TaxConfig,
    AmortizationRow,
    AmortizationSchedule,
)

__all__ = [
    "SimulatorValidationError",
    "round_currency",
    "format_fcfa",
    "parse_fcfa",
    "annual_to_monthly_rate",
    "monthly_to_annual_rate",
    "format_pct",
    "month_to_calendar",
    "format_month_label",
    "validate_positive_number",
    "validate_rate",
    "validate_lease_term",
    "validate_lease_deposit",
    "validate_batch_step",
    "FinancingAssumptions",
    "ProcurementAssumptions",
    "CashSaleAssumptions",
    "LeaseAssumptions",
    "ExploitationAssumptions",
    "ProtectionCostConfig",
    "ProtectionCostItem",
    "TaxConfig",
    "AmortizationRow",
    "AmortizationSchedule",
]
