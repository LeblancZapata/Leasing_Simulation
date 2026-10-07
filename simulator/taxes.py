"""Configurable tax calculation engine adhering strictly to AGENTS.md Rule 4.

Statutory Reference:
- Cameroon Directorate General of Taxation (DGI), General Tax Code (CGI), updated 1 January 2026.
- Standard General VAT Rate: 19.25% (Art. 149 CGI).
- All tax and regulatory rates are configurable by the user and tagged with clear provenance:
  'verified_statutory_rate' vs 'input_assumption'.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional

from simulator.primitives import (
    validate_positive_number,
    validate_rate,
    SimulatorValidationError,
)

DGI_GTC_2026_REFERENCE = (
    "Cameroon General Tax Code (Code Général des Impôts - CGI), updated 1 January 2026 (DGI)"
)

# Statutory baseline from Cameroon 2026 GTC Art. 149
STATUTORY_VAT_RATE: float = 0.1925


class TaxProvenance(str, Enum):
    """Origin and legal status of tax/legal parameters."""
    VERIFIED_STATUTORY = "verified_statutory_rate"
    INPUT_ASSUMPTION = "input_assumption"


@dataclass
class TaxParameterMetadata:
    """Descriptor metadata documenting legal source and status of tax parameters."""
    name: str
    provenance: TaxProvenance
    legal_reference: str
    description: str


TAX_METADATA_REGISTRY: Dict[str, TaxParameterMetadata] = {
    "vat_rate": TaxParameterMetadata(
        name="Value Added Tax (VAT / TVA)",
        provenance=TaxProvenance.VERIFIED_STATUTORY,
        legal_reference="Cameroon GTC 2026 Art. 149 (17.5% principal + 10% CAC surcharge = 19.25%)",
        description="Standard indirect tax rate applied to non-exempt goods and commercial leases.",
    ),
    "vat_recoverable": TaxParameterMetadata(
        name="VAT Recoverability",
        provenance=TaxProvenance.INPUT_ASSUMPTION,
        legal_reference="Depends on taxpayer regime (Régime Réel vs Simplifié) and vehicle classification.",
        description="Toggle whether VAT paid on acquisition or charged on lease is recoverable or deductible.",
    ),
    "corporate_income_tax_rate": TaxParameterMetadata(
        name="Corporate Income Tax (IS)",
        provenance=TaxProvenance.INPUT_ASSUMPTION,
        legal_reference="Standard statutory rate is typically 30% (+ CAC), but effective rates vary by regime and deductions.",
        description="Effective corporate income tax rate applied against net taxable operating profits.",
    ),
    "registration_fees_per_truck": TaxParameterMetadata(
        name="Title & Vehicle Registration Administrative Fees",
        provenance=TaxProvenance.INPUT_ASSUMPTION,
        legal_reference="Administrative tariff varies by chassis weight, horsepower (CV), and region.",
        description="Flat administrative charges for title, registration, and license plate.",
    ),
    "annual_road_tax": TaxParameterMetadata(
        name="Annual Vehicle Axle / Road Tax (Taxe à l'Essieu)",
        provenance=TaxProvenance.INPUT_ASSUMPTION,
        legal_reference="Cameroon GTC 2026 provisions on heavy transport equipment axle taxes.",
        description="Annual local road maintenance tax levied per commercial dump truck.",
    ),
}


@dataclass
class TaxConfiguration:
    """Comprehensive configurable tax and fiscal parameters."""
    vat_rate: float = STATUTORY_VAT_RATE
    vat_recoverable: bool = False
    corporate_income_tax_rate: float = 0.30
    registration_fees_per_truck: float = 500_000.0
    annual_road_tax: float = 150_000.0
    customs_import_tariff_rate: float = 0.0  # Usually rolled into vehicle landed cost

    def __post_init__(self):
        validate_rate("VAT rate", self.vat_rate, min_rate=0.0, max_rate=0.50)
        validate_rate("Corporate income tax rate", self.corporate_income_tax_rate, min_rate=0.0, max_rate=0.60)
        validate_positive_number("Registration fees per truck", self.registration_fees_per_truck, allow_zero=True)
        validate_positive_number("Annual road tax", self.annual_road_tax, allow_zero=True)
        validate_rate("Customs import tariff rate", self.customs_import_tariff_rate, min_rate=0.0, max_rate=1.0)


def calculate_vat(taxable_base: float, config: TaxConfiguration) -> float:
    """Calculate VAT amount on a taxable transaction base.
    
    If vat_recoverable is True, net unrecoverable cost to the business is 0.0.
    Otherwise, cost is taxable_base * vat_rate.
    """
    validate_positive_number("Taxable base", taxable_base, allow_zero=True)
    if config.vat_recoverable:
        return 0.0
    return taxable_base * config.vat_rate


def calculate_corporate_income_tax(taxable_profit: float, config: TaxConfiguration) -> float:
    """Calculate Corporate Income Tax (CIT) on taxable positive profit."""
    if taxable_profit <= 0.0:
        return 0.0
    return taxable_profit * config.corporate_income_tax_rate


def calculate_tax_impact(
    gross_revenue: float,
    deductible_expenses: float,
    config: TaxConfiguration,
) -> Dict[str, Any]:
    """Calculate net after-tax financial result and effective fiscal burden."""
    validate_positive_number("Gross revenue", gross_revenue, allow_zero=True)
    validate_positive_number("Deductible expenses", deductible_expenses, allow_zero=True)

    pre_tax_profit = gross_revenue - deductible_expenses
    cit_amount = calculate_corporate_income_tax(pre_tax_profit, config)
    net_after_tax_profit = pre_tax_profit - cit_amount

    effective_rate = cit_amount / pre_tax_profit if pre_tax_profit > 0 else 0.0

    return {
        "gross_revenue": gross_revenue,
        "deductible_expenses": deductible_expenses,
        "pre_tax_profit": pre_tax_profit,
        "corporate_income_tax": cit_amount,
        "net_after_tax_profit": net_after_tax_profit,
        "effective_tax_rate": effective_rate,
        "is_profitable": pre_tax_profit > 0.0,
    }
