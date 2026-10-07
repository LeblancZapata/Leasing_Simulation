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

from simulator.loan import (
    calculate_monthly_payment,
    generate_amortization_schedule,
    generate_loan_schedule_from_assumptions,
    schedule_to_dataframe,
)

from simulator.acquisition import (
    LANDED_COST_PRESETS,
    DEFAULT_BATCH_STEP,
    BatchProcurementEvaluation,
    calculate_purchasable_trucks,
    evaluate_batch_procurement,
    evaluate_procurement_from_assumptions,
    find_earliest_affordable_month,
)

from simulator.sale import (
    MARKET_BENCHMARK_PRICES,
    CashSalePricingResult,
    CashSaleEconomics,
    calculate_financing_carry,
    calculate_price_floor,
    calculate_recommended_price,
    evaluate_cash_sale_pricing,
    evaluate_sale_price_economics,
    generate_market_comparison_table,
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
    "calculate_monthly_payment",
    "generate_amortization_schedule",
    "generate_loan_schedule_from_assumptions",
    "schedule_to_dataframe",
    "LANDED_COST_PRESETS",
    "DEFAULT_BATCH_STEP",
    "BatchProcurementEvaluation",
    "calculate_purchasable_trucks",
    "evaluate_batch_procurement",
    "evaluate_procurement_from_assumptions",
    "find_earliest_affordable_month",
    "MARKET_BENCHMARK_PRICES",
    "CashSalePricingResult",
    "CashSaleEconomics",
    "calculate_financing_carry",
    "calculate_price_floor",
    "calculate_recommended_price",
    "evaluate_cash_sale_pricing",
    "evaluate_sale_price_economics",
    "generate_market_comparison_table",
]



