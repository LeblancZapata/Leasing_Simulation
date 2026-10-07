"""Truck procurement and discrete batch purchasing engine."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional, List, Dict, Union

from simulator.primitives import (
    validate_positive_number,
    validate_rate,
    SimulatorValidationError,
)
from simulator.models import (
    FinancingAssumptions,
    ProcurementAssumptions,
)

# Canonical presets defined in Section 4.2 / Section 13
LANDED_COST_PRESETS: Dict[str, float] = {
    "Best": 38_000_000.0,
    "Average": 40_000_000.0,
    "Worst": 42_000_000.0,
}

DEFAULT_BATCH_STEP: int = 5


@dataclass
class BatchProcurementEvaluation:
    """Evaluation result for discrete batch procurement affordability."""
    available_cash: float
    reserve: float
    net_available_cash: float
    unit_cost: float
    batch_step: int
    affordable_trucks_raw: int
    purchasable_trucks: int
    total_batch_cost: float
    remaining_cash: float
    next_batch_trucks: int
    next_batch_required_cash: float
    cash_shortfall: float
    is_batch_affordable: bool

    @property
    def unallocated_cash_after_reserve(self) -> float:
        """Cash remaining above the required reserve after purchasing complete batches."""
        return max(0.0, self.remaining_cash - self.reserve)


def calculate_purchasable_trucks(
    available_cash: float,
    reserve: float,
    unit_cost: float,
    batch_step: int = DEFAULT_BATCH_STEP,
) -> int:
    """Calculate the number of trucks that can be purchased in discrete complete batches.
    
    Formula:
        net_cash = available_cash - reserve
        affordable_trucks = floor(net_cash / unit_cost)
        purchasable_trucks = floor(affordable_trucks / batch_step) * batch_step
        
    Guarantees:
        - Never silently buys a partial batch (e.g. 6, 7, 8, 9 trucks are reduced to 5).
        - If net_cash < unit_cost * batch_step, returns 0.
        - Preserves the cash reserve strictly.
    """
    validate_positive_number("Available cash", available_cash, allow_zero=True)
    validate_positive_number("Reserve", reserve, allow_zero=True)
    validate_positive_number("Unit cost", unit_cost, allow_zero=False)
    if batch_step <= 0:
        raise SimulatorValidationError(f"Batch step must be a positive integer, got {batch_step}")

    net_cash = available_cash - reserve
    if net_cash < unit_cost * batch_step:
        return 0

    affordable_raw = math.floor(net_cash / unit_cost)
    purchasable = (affordable_raw // batch_step) * batch_step
    return int(purchasable)


def evaluate_batch_procurement(
    available_cash: float,
    reserve: float,
    landed_cost: float,
    contingency_rate: float = 0.0,
    contingency_amount: float = 0.0,
    batch_step: int = DEFAULT_BATCH_STEP,
) -> BatchProcurementEvaluation:
    """Perform a full evaluation of discrete batch procurement affordability and shortfall."""
    validate_positive_number("Available cash", available_cash, allow_zero=True)
    validate_positive_number("Reserve", reserve, allow_zero=True)
    validate_positive_number("Landed cost", landed_cost, allow_zero=False)
    validate_rate("Contingency rate", contingency_rate, min_rate=0.0, max_rate=1.0)
    validate_positive_number("Contingency amount", contingency_amount, allow_zero=True)
    if batch_step <= 0:
        raise SimulatorValidationError(f"Batch step must be a positive integer, got {batch_step}")

    unit_cost = landed_cost * (1.0 + contingency_rate) + contingency_amount
    net_available_cash = max(0.0, available_cash - reserve)

    if net_available_cash >= unit_cost:
        affordable_trucks_raw = math.floor(net_available_cash / unit_cost)
    else:
        affordable_trucks_raw = 0

    purchasable_trucks = (affordable_trucks_raw // batch_step) * batch_step
    total_batch_cost = purchasable_trucks * unit_cost
    remaining_cash = available_cash - total_batch_cost

    next_batch_trucks = purchasable_trucks + batch_step
    # Required cash to reach the next batch level while preserving reserve:
    next_batch_required_cash = (next_batch_trucks * unit_cost) + reserve
    cash_shortfall = max(0.0, next_batch_required_cash - available_cash)
    is_batch_affordable = purchasable_trucks > 0

    return BatchProcurementEvaluation(
        available_cash=available_cash,
        reserve=reserve,
        net_available_cash=net_available_cash,
        unit_cost=unit_cost,
        batch_step=batch_step,
        affordable_trucks_raw=affordable_trucks_raw,
        purchasable_trucks=purchasable_trucks,
        total_batch_cost=total_batch_cost,
        remaining_cash=remaining_cash,
        next_batch_trucks=next_batch_trucks,
        next_batch_required_cash=next_batch_required_cash,
        cash_shortfall=cash_shortfall,
        is_batch_affordable=is_batch_affordable,
    )


def evaluate_procurement_from_assumptions(
    available_cash: float,
    financing: FinancingAssumptions,
    procurement: ProcurementAssumptions,
) -> BatchProcurementEvaluation:
    """Convenience helper to evaluate procurement directly from FinancingAssumptions and ProcurementAssumptions."""
    return evaluate_batch_procurement(
        available_cash=available_cash,
        reserve=financing.min_cash_reserve,
        landed_cost=procurement.landed_cost,
        contingency_rate=procurement.contingency_rate,
        contingency_amount=procurement.contingency_amount,
        batch_step=procurement.batch_step,
    )


def find_earliest_affordable_month(
    projected_cash_by_month: Union[List[float], Dict[int, float]],
    reserve: float,
    unit_cost: float,
    batch_step: int = DEFAULT_BATCH_STEP,
    target_batches: int = 1,
) -> Optional[int]:
    """Find the earliest month index where enough cash is projected to purchase target_batches while maintaining reserve.
    
    If projected_cash_by_month is a list, 0-index or 1-index can be used.
    If it is a dict, keys are month indices.
    Returns None if the target batch is never affordable within the horizon.
    """
    required_cash = (target_batches * batch_step * unit_cost) + reserve

    if isinstance(projected_cash_by_month, dict):
        for month, cash in sorted(projected_cash_by_month.items()):
            if cash >= required_cash:
                return month
        return None
    else:
        for idx, cash in enumerate(projected_cash_by_month):
            if cash >= required_cash:
                return idx
        return None
