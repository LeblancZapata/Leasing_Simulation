"""Portfolio state and vehicle lifecycle records."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class StrategyType(str, Enum):
    """The strategic allocation pathway assigned to a vehicle."""
    CASH_SALE = "CASH_SALE"
    LEASING = "LEASING"
    EXPLOITATION = "EXPLOITATION"


class TruckState(str, Enum):
    """Lifecycle states of a truck as specified in Section 11.1."""
    # Lifecycle: AVAILABLE -> LEASED -> COMPLETED / DEFAULTED -> RECOVERED / SOLD
    AVAILABLE = "AVAILABLE"
    LEASED = "LEASED"
    COMPLETED = "COMPLETED"
    DEFAULTED = "DEFAULTED"
    RECOVERED_SOLD = "RECOVERED_SOLD"
    # Lifecycle: AVAILABLE -> EXPLOITATION -> ACTIVE / DOWNTIME
    EXPLOITATION_ACTIVE = "EXPLOITATION_ACTIVE"
    EXPLOITATION_DOWNTIME = "EXPLOITATION_DOWNTIME"
    # Lifecycle: AVAILABLE -> SOLD
    SOLD = "SOLD"


@dataclass
class TruckRecord:
    """Individual truck state record as specified in Section 11.1."""
    id: int
    strategy: StrategyType
    acquisition_month: int
    acquisition_cost: float
    current_state: TruckState
    # Strategy B (Lease) attributes
    lease_term_months: Optional[int] = None
    lease_start_month: Optional[int] = None
    monthly_installment: float = 0.0
    remaining_receivable: float = 0.0
    # Strategy A (Sale) attributes
    sale_month: Optional[int] = None
    sale_price: float = 0.0
    holding_period_months: int = 1
    # Strategy C (Exploitation) attributes
    net_monthly_profit: float = 0.0

    @property
    def is_active(self) -> bool:
        """True if the truck is generating cash or in active deployment."""
        return self.current_state in (
            TruckState.LEASED,
            TruckState.EXPLOITATION_ACTIVE,
            TruckState.EXPLOITATION_DOWNTIME,
            TruckState.AVAILABLE,
        )


@dataclass
class MonthlyPortfolioSnapshot:
    """Deterministic snapshot of portfolio financial metrics at month m (Section 11)."""
    month: int
    opening_cash: float
    opening_debt: float
    # Inflows
    inflows_lease_deposits: float
    inflows_lease_installments: float
    inflows_exploitation: float
    inflows_sales: float
    total_inflows: float
    # Outflows
    outflows_operating: float
    outflows_protection: float
    outflows_debt_principal: float
    outflows_debt_interest: float
    outflows_debt_service: float
    total_outflows: float
    # Cash before reinvestment
    cash_before_reinvestment: float
    # Reinvestment
    reinvestment_trucks_purchased: int
    reinvestment_cost: float
    # Closing positions
    closing_cash: float
    closing_debt: float
    # Fleet counts and balances
    total_trucks_owned: int
    active_trucks_count: int
    trucks_by_strategy: Dict[str, int]
    lease_receivables_outstanding: float
    cash_reserve_required: float
    cash_surplus_above_reserve: float
    next_batch_shortfall: float
