"""Domain data models and structured configurations for Dump Truck Simulator."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from simulator.primitives import (
    SimulatorValidationError,
    validate_positive_number,
    validate_rate,
    validate_lease_term,
    validate_lease_deposit,
    validate_batch_step,
    annual_to_monthly_rate,
)


@dataclass
class FinancingAssumptions:
    """Financing assumptions for bank loan and cash management."""
    bank_loan_amount: float = 500_000_000.0
    annual_financing_rate: float = 0.15
    loan_term_months: int = 36
    bank_arrangement_fees: float = 0.0
    other_bank_charges: float = 0.0
    starting_cash: float = 0.0
    min_cash_reserve: float = 20_000_000.0

    def __post_init__(self):
        validate_positive_number("Bank loan amount", self.bank_loan_amount, allow_zero=True)
        validate_rate("Annual financing rate", self.annual_financing_rate, min_rate=0.0, max_rate=1.0)
        if self.loan_term_months <= 0:
            raise SimulatorValidationError(f"Loan term must be positive, got {self.loan_term_months}")
        validate_positive_number("Bank arrangement fees", self.bank_arrangement_fees, allow_zero=True)
        validate_positive_number("Other bank charges", self.other_bank_charges, allow_zero=True)
        validate_positive_number("Starting cash", self.starting_cash, allow_zero=True)
        validate_positive_number("Minimum cash reserve", self.min_cash_reserve, allow_zero=True)

    @property
    def monthly_interest_rate(self) -> float:
        return annual_to_monthly_rate(self.annual_financing_rate)


@dataclass
class ProcurementAssumptions:
    """Truck procurement and discrete batch purchasing assumptions."""
    landed_cost: float = 40_000_000.0
    batch_step: int = 5
    contingency_rate: float = 0.0
    contingency_amount: float = 0.0

    def __post_init__(self):
        validate_positive_number("Truck landed cost", self.landed_cost, allow_zero=False)
        if self.batch_step <= 0:
            raise SimulatorValidationError(f"Batch step must be positive integer, got {self.batch_step}")
        validate_rate("Contingency rate", self.contingency_rate, min_rate=0.0, max_rate=1.0)
        validate_positive_number("Contingency amount", self.contingency_amount, allow_zero=True)

    @property
    def effective_unit_cost(self) -> float:
        """Total landed cost per truck including contingency."""
        return self.landed_cost * (1.0 + self.contingency_rate) + self.contingency_amount


@dataclass
class CashSaleAssumptions:
    """Strategy A: Cash-sale pricing assumptions."""
    target_markup: float = 0.15
    holding_period_months: int = 1
    acquisition_costs: float = 0.0
    financing_carry: float = 0.0
    selling_costs: float = 0.0
    transaction_costs: float = 0.0
    risk_reserve: float = 0.0
    minimum_profit: float = 0.0

    def __post_init__(self):
        validate_rate("Target markup", self.target_markup, min_rate=0.0, max_rate=2.0)
        if self.holding_period_months < 0:
            raise SimulatorValidationError("Holding period cannot be negative")
        validate_positive_number("Acquisition costs", self.acquisition_costs, allow_zero=True)
        validate_positive_number("Financing carry", self.financing_carry, allow_zero=True)
        validate_positive_number("Selling costs", self.selling_costs, allow_zero=True)
        validate_positive_number("Transaction costs", self.transaction_costs, allow_zero=True)
        validate_positive_number("Risk reserve", self.risk_reserve, allow_zero=True)
        validate_positive_number("Minimum profit", self.minimum_profit, allow_zero=True)


@dataclass
class LeaseAssumptions:
    """Strategy B: Customer leasing / installment plan assumptions."""
    term_months: int = 24
    initial_deposit: float = 10_000_000.0
    total_contract_price: Optional[float] = None
    max_monthly_payment: Optional[float] = None
    target_annual_return: float = 0.25
    early_payoff_month: Optional[int] = None
    late_payment_penalty_rate: float = 0.0
    default_probability: float = 0.0
    recovery_cost: float = 0.0
    recovery_time_months: int = 2
    recovery_value: float = 0.0

    def __post_init__(self):
        validate_lease_term(self.term_months)
        validate_lease_deposit(self.initial_deposit)
        if self.total_contract_price is not None:
            validate_positive_number("Total contract price", self.total_contract_price, allow_zero=False)
            if self.total_contract_price < self.initial_deposit:
                raise SimulatorValidationError(
                    f"Total contract price ({self.total_contract_price}) cannot be less than initial deposit ({self.initial_deposit})"
                )
        if self.max_monthly_payment is not None:
            validate_positive_number("Max monthly payment", self.max_monthly_payment, allow_zero=False)
        validate_rate("Target annual return", self.target_annual_return, min_rate=0.0, max_rate=2.0)
        validate_rate("Default probability", self.default_probability, min_rate=0.0, max_rate=1.0)


@dataclass
class ExploitationAssumptions:
    """Strategy C: Company fleet direct exploitation assumptions."""
    net_monthly_profit_per_truck: float = 2_500_000.0
    downtime_allowance_rate: float = 0.0
    gps_monthly_cost: float = 0.0
    other_monthly_overhead: float = 0.0

    def __post_init__(self):
        validate_positive_number("Net monthly profit per truck", self.net_monthly_profit_per_truck, allow_zero=True)
        validate_rate("Downtime allowance rate", self.downtime_allowance_rate, min_rate=0.0, max_rate=1.0)
        validate_positive_number("GPS monthly cost", self.gps_monthly_cost, allow_zero=True)
        validate_positive_number("Other monthly overhead", self.other_monthly_overhead, allow_zero=True)

    @property
    def effective_monthly_cash_per_truck(self) -> float:
        """Net monthly operational cash per truck adjusting for downtime and direct recurring costs."""
        operational_net = self.net_monthly_profit_per_truck * (1.0 - self.downtime_allowance_rate)
        return max(0.0, operational_net - self.gps_monthly_cost - self.other_monthly_overhead)


@dataclass
class ProtectionCostItem:
    """Individual security/protection cost item for leased trucks."""
    name: str
    amount: float
    is_percentage: bool = False  # If True, amount is decimal percentage of financed receivable
    is_recurring_monthly: bool = False
    enabled: bool = True


@dataclass
class ProtectionCostConfig:
    """Collection of configurable protection and security costs for leasing."""
    gps_installation: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("GPS Installation", 150_000.0, False, False, True)
    )
    gps_monthly_sub: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("GPS Monthly Subscription", 15_000.0, False, True, True)
    )
    contract_preparation: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("Document / Contract Preparation", 250_000.0, False, False, True)
    )
    customer_credit_check: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("Customer Verification / Credit Check", 100_000.0, False, False, True)
    )
    insurance_upfront: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("Mandatory Annual Insurance Premium", 1_200_000.0, False, False, True)
    )
    pre_handover_inspection: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("Pre-handover Vehicle Inspection", 100_000.0, False, False, True)
    )
    legal_registration: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("Title / Security Registration", 300_000.0, False, False, True)
    )
    default_reserve: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("Default / Collection Reserve", 0.05, True, False, True)
    )
    repossession_reserve: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("Repossession / Recovery Reserve", 500_000.0, False, False, True)
    )
    legal_enforcement_reserve: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("Legal Enforcement Reserve", 300_000.0, False, False, True)
    )
    payment_processing_fees: ProtectionCostItem = field(
        default_factory=lambda: ProtectionCostItem("Payment Processing / Bank Charges", 0.01, True, False, False)
    )

    def total_upfront_fixed_protection(self) -> float:
        """Total fixed upfront protection cost per truck."""
        total = 0.0
        for item in [
            self.gps_installation,
            self.contract_preparation,
            self.customer_credit_check,
            self.insurance_upfront,
            self.pre_handover_inspection,
            self.legal_registration,
            self.repossession_reserve,
            self.legal_enforcement_reserve,
        ]:
            if item.enabled and not item.is_percentage and not item.is_recurring_monthly:
                total += item.amount
        return total

    def total_variable_protection_rate(self) -> float:
        """Total variable protection rate as fraction of financed receivable."""
        rate = 0.0
        for item in [self.default_reserve, self.payment_processing_fees]:
            if item.enabled and item.is_percentage:
                rate += item.amount
        return rate


@dataclass
class TaxConfig:
    """Configurable tax and regulatory cost assumptions."""
    vat_rate: float = 0.1925  # Statutory Cameroon General Tax Code 2026 standard rate
    vat_recoverable: bool = False
    corporate_income_tax_rate: float = 0.30
    registration_fees_per_truck: float = 500_000.0
    annual_vehicle_road_tax: float = 150_000.0


@dataclass
class AmortizationRow:
    """Monthly record in loan amortization schedule."""
    month: int
    opening_balance: float
    payment: float
    interest: float
    principal: float
    closing_balance: float


@dataclass
class AmortizationSchedule:
    """Complete loan amortization schedule and summary."""
    rows: List[AmortizationRow]
    total_payment: float
    total_interest: float
    total_principal: float
    monthly_payment: float
