"""Financial primitives, money/percentage/date helpers, and core validations."""
from __future__ import annotations
import math
from typing import Optional, Tuple, Iterable


class SimulatorValidationError(ValueError):
    """Raised when an input assumption or financial constraint fails validation."""
    pass


# ---------------------------------------------------------------------------
# Money / Currency Helpers (FCFA)
# ---------------------------------------------------------------------------

def round_currency(amount: float, decimals: int = 0) -> float:
    """Round a currency amount to specified decimals (default 0 for FCFA integers)."""
    if math.isnan(amount) or math.isinf(amount):
        raise SimulatorValidationError(f"Invalid currency amount: {amount}")
    return round(amount, decimals)


def format_fcfa(amount: float, compact: bool = False, include_symbol: bool = True) -> str:
    """Format an amount into FCFA currency string.
    
    Examples:
        format_fcfa(500000000) -> "500,000,000 FCFA"
        format_fcfa(40000000, compact=True) -> "40.0M FCFA"
        format_fcfa(1500000000, compact=True) -> "1.50B FCFA"
    """
    if math.isnan(amount) or math.isinf(amount):
        return "N/A"

    symbol = " FCFA" if include_symbol else ""

    if compact:
        abs_amt = abs(amount)
        sign = "-" if amount < 0 else ""
        if abs_amt >= 1_000_000_000:
            val = abs_amt / 1_000_000_000
            return f"{sign}{val:.2f}B{symbol}"
        elif abs_amt >= 1_000_000:
            val = abs_amt / 1_000_000
            # format e.g. 40M if integer, or 40.5M
            if val.is_integer():
                return f"{sign}{int(val)}M{symbol}"
            return f"{sign}{val:.1f}M{symbol}"
        elif abs_amt >= 1_000:
            val = abs_amt / 1_000
            if val.is_integer():
                return f"{sign}{int(val)}k{symbol}"
            return f"{sign}{val:.1f}k{symbol}"

    return f"{amount:,.0f}{symbol}"


def parse_fcfa(value: str | float | int) -> float:
    """Parse string representations of FCFA amounts such as '500M', '40,000,000 FCFA', '1.5B'."""
    if isinstance(value, (int, float)):
        return float(value)

    cleaned = value.strip().upper().replace("FCFA", "").replace("CFA", "").replace(",", "").replace(" ", "").strip()
    if not cleaned:
        raise SimulatorValidationError("Cannot parse empty amount string")

    multiplier = 1.0
    if cleaned.endswith("B"):
        multiplier = 1_000_000_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("M"):
        multiplier = 1_000_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("K"):
        multiplier = 1_000.0
        cleaned = cleaned[:-1]

    try:
        val = float(cleaned) * multiplier
    except ValueError as e:
        raise SimulatorValidationError(f"Invalid FCFA amount string: '{value}'") from e

    if math.isnan(val) or math.isinf(val):
        raise SimulatorValidationError(f"Invalid numeric amount in '{value}'")

    return val


# ---------------------------------------------------------------------------
# Percentage & Rate Helpers
# ---------------------------------------------------------------------------

def annual_to_monthly_rate(annual_rate: float) -> float:
    """Convert nominal annual interest rate to monthly interest rate:
    
    monthly_rate = annual_rate / 12
    """
    if annual_rate < 0:
        raise SimulatorValidationError(f"Annual rate cannot be negative, got {annual_rate}")
    if math.isnan(annual_rate) or math.isinf(annual_rate):
        raise SimulatorValidationError(f"Annual rate is invalid: {annual_rate}")
    return annual_rate / 12.0


def monthly_to_annual_rate(monthly_rate: float) -> float:
    """Convert monthly nominal rate to annual nominal rate."""
    if monthly_rate < 0:
        raise SimulatorValidationError(f"Monthly rate cannot be negative, got {monthly_rate}")
    return monthly_rate * 12.0


def format_pct(rate: float, decimals: int = 2) -> str:
    """Format decimal rate to percentage string (e.g. 0.20 -> '20.00%')."""
    if math.isnan(rate) or math.isinf(rate):
        return "N/A"
    return f"{rate * 100:.{decimals}f}%"


# ---------------------------------------------------------------------------
# Date / Simulation Month Helpers
# ---------------------------------------------------------------------------

def month_to_calendar(month_index: int, start_year: int = 2026, start_month: int = 1) -> Tuple[int, int]:
    """Convert a 1-indexed (or 0-indexed if month_index=0) month to (year, month).
    
    If month_index == 0, returns (start_year, start_month).
    For month_index >= 1, month_index 1 is the first operational month.
    """
    if month_index < 0:
        raise SimulatorValidationError(f"Month index cannot be negative, got {month_index}")

    if month_index == 0:
        return (start_year, start_month)

    total_months = (start_year * 12 + (start_month - 1)) + (month_index - 1)
    year = total_months // 12
    month = (total_months % 12) + 1
    return (year, month)


def format_month_label(month_index: int, start_year: int = 2026, start_month: int = 1) -> str:
    """Format month index to human-readable label, e.g. 'Month 1 (Jan 2026)'."""
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    year, month = month_to_calendar(month_index, start_year, start_month)
    month_str = month_names[month - 1]
    if month_index == 0:
        return f"Month 0 (Initial - {month_str} {year})"
    return f"Month {month_index} ({month_str} {year})"


# ---------------------------------------------------------------------------
# Common Validation Functions
# ---------------------------------------------------------------------------

def validate_positive_number(name: str, value: float, allow_zero: bool = True) -> float:
    """Validate that a number is non-negative (or strictly positive if allow_zero=False)."""
    if math.isnan(value) or math.isinf(value):
        raise SimulatorValidationError(f"{name} must be a valid finite number, got {value}")
    if allow_zero and value < 0:
        raise SimulatorValidationError(f"{name} cannot be negative, got {value}")
    if not allow_zero and value <= 0:
        raise SimulatorValidationError(f"{name} must be strictly positive, got {value}")
    return float(value)


def validate_rate(name: str, value: float, min_rate: float = 0.0, max_rate: float = 1.0) -> float:
    """Validate that a rate is within allowable bounds [min_rate, max_rate]."""
    if math.isnan(value) or math.isinf(value):
        raise SimulatorValidationError(f"{name} must be a valid finite rate, got {value}")
    if value < min_rate or value > max_rate:
        raise SimulatorValidationError(
            f"{name} must be between {min_rate:.1%} and {max_rate:.1%}, got {value:.1%}"
        )
    return float(value)


def validate_lease_term(term_months: int, allowed_terms: Iterable[int] = (6, 12, 18, 24)) -> int:
    """Validate that lease term is one of the allowed terms (6, 12, 18, 24 months in V1)."""
    if term_months not in allowed_terms:
        allowed_str = ", ".join(str(t) for t in allowed_terms)
        raise SimulatorValidationError(
            f"Lease term must be one of [{allowed_str}] months, got {term_months}"
        )
    return int(term_months)


def validate_lease_deposit(deposit: float, min_deposit: float = 10_000_000.0) -> float:
    """Validate that the lease initial deposit is at least the statutory minimum (10M FCFA)."""
    validate_positive_number("Lease deposit", deposit, allow_zero=False)
    if deposit < min_deposit:
        raise SimulatorValidationError(
            f"Initial lease deposit cannot be below {format_fcfa(min_deposit)}, got {format_fcfa(deposit)}"
        )
    return float(deposit)


def validate_batch_step(truck_count: int, batch_step: int = 5) -> int:
    """Validate that procurement truck count is a non-negative multiple of batch_step."""
    if truck_count < 0:
        raise SimulatorValidationError(f"Truck count cannot be negative, got {truck_count}")
    if truck_count % batch_step != 0:
        raise SimulatorValidationError(
            f"Truck count must be a multiple of {batch_step}, got {truck_count}"
        )
    return int(truck_count)

