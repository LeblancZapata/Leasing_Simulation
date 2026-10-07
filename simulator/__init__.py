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

from simulator.lease import (
    ALLOWED_LEASE_TERMS,
    MINIMUM_LEASE_DEPOSIT,
    OPTIMAL_ANNUAL_LEASING_RATE,
    LeaseScheduleRow,
    LeaseEvaluationResult,
    calculate_lease_price_first,
    calculate_lease_payment_first,
    calculate_dynamic_recommended_lease_price,
    lease_schedule_to_dataframe,
    ClientLeaseOption,
    generate_client_lease_options,
)

from simulator.exploitation import (
    EXPLOITATION_PROFIT_PRESETS,
    ExploitationScheduleRow,
    ExploitationEvaluationResult,
    calculate_effective_monthly_cash,
    calculate_payback_period,
    evaluate_exploitation,
    exploitation_schedule_to_dataframe,
)

from simulator.costs import (
    LeaseProtectionBreakdown,
    calculate_lease_protection,
    FleetOperationalCostConfig,
)

from simulator.taxes import (
    DGI_GTC_2026_REFERENCE,
    STATUTORY_VAT_RATE,
    TaxProvenance,
    TaxParameterMetadata,
    TAX_METADATA_REGISTRY,
    TaxConfiguration,
    calculate_vat,
    calculate_corporate_income_tax,
    calculate_tax_impact,
)

from simulator.portfolio import (
    StrategyType,
    TruckState,
    TruckRecord,
    MonthlyPortfolioSnapshot,
)

from simulator.simulation import (
    SimulationConfig,
    SimulationResult,
    run_portfolio_simulation,
    simulation_to_dataframe,
)

from simulator.metrics import (
    calculate_roi,
    calculate_cash_on_cash,
    calculate_dscr,
    StrategyMetrics,
    StrategyRecommendation,
    compare_strategies,
)

from simulator.scenarios import (
    DEFAULT_SCENARIO_COSTS,
    DEFAULT_SCENARIO_RATES,
    DEFAULT_SCENARIO_TERMS,
    run_scenario_matrix,
    run_preset_comparison,
)

from simulator.analyst import (
    PortfolioPlan,
    evaluate_single_plan,
    run_business_analyst_optimizer,
    generate_analyst_insights,
)

from simulator.i18n import (
    t,
    TRANSLATIONS,
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
    "ALLOWED_LEASE_TERMS",
    "MINIMUM_LEASE_DEPOSIT",
    "OPTIMAL_ANNUAL_LEASING_RATE",
    "LeaseScheduleRow",
    "LeaseEvaluationResult",
    "calculate_lease_price_first",
    "calculate_lease_payment_first",
    "calculate_dynamic_recommended_lease_price",
    "lease_schedule_to_dataframe",
    "ClientLeaseOption",
    "generate_client_lease_options",
    "EXPLOITATION_PROFIT_PRESETS",
    "ExploitationScheduleRow",
    "ExploitationEvaluationResult",
    "calculate_effective_monthly_cash",
    "calculate_payback_period",
    "evaluate_exploitation",
    "exploitation_schedule_to_dataframe",
    "LeaseProtectionBreakdown",
    "calculate_lease_protection",
    "FleetOperationalCostConfig",
    "DGI_GTC_2026_REFERENCE",
    "STATUTORY_VAT_RATE",
    "TaxProvenance",
    "TaxParameterMetadata",
    "TAX_METADATA_REGISTRY",
    "TaxConfiguration",
    "calculate_vat",
    "calculate_corporate_income_tax",
    "calculate_tax_impact",
    "StrategyType",
    "TruckState",
    "TruckRecord",
    "MonthlyPortfolioSnapshot",
    "SimulationConfig",
    "SimulationResult",
    "run_portfolio_simulation",
    "simulation_to_dataframe",
    "calculate_roi",
    "calculate_cash_on_cash",
    "calculate_dscr",
    "StrategyMetrics",
    "StrategyRecommendation",
    "compare_strategies",
    "DEFAULT_SCENARIO_COSTS",
    "DEFAULT_SCENARIO_RATES",
    "DEFAULT_SCENARIO_TERMS",
    "run_scenario_matrix",
    "run_preset_comparison",
    "t",
    "TRANSLATIONS",
]
