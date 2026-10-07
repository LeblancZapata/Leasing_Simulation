"""Unit and regression tests for costs, security protection, and configurable taxes."""
import pytest

from simulator.primitives import SimulatorValidationError
from simulator.models import ProtectionCostConfig, ProtectionCostItem
from simulator.costs import (
    calculate_lease_protection,
    FleetOperationalCostConfig,
)
from simulator.taxes import (
    DGI_GTC_2026_REFERENCE,
    STATUTORY_VAT_RATE,
    TaxProvenance,
    TAX_METADATA_REGISTRY,
    TaxConfiguration,
    calculate_vat,
    calculate_corporate_income_tax,
    calculate_tax_impact,
)


# ===========================================================================
# Protection and Security Costs Tests
# ===========================================================================

def test_lease_protection_cost_breakdown():
    """Section 9.1: Verify protection costs per leased truck with fixed, variable, and recurring items."""
    config = ProtectionCostConfig()
    financed_receivable = 48_000_000.0
    term_months = 24

    breakdown = calculate_lease_protection(config, financed_receivable, term_months)

    # Fixed upfront items:
    # GPS install (150k) + Contract prep (250k) + Credit check (100k) + Insurance (1.2M)
    # + Pre-inspection (100k) + Legal registration (300k) + Repossession reserve (500k)
    # + Legal enforcement reserve (300k) = 2.9M
    assert breakdown.fixed_upfront_total == 2_900_000.0

    # Variable: default_reserve (5%) enabled = 0.05 * 48M = 2,400,000
    assert breakdown.variable_rate_total == pytest.approx(0.05)
    assert breakdown.variable_amount == pytest.approx(2_400_000.0)

    # Recurring: GPS monthly sub (15k/month) * 24 = 360,000
    assert breakdown.monthly_recurring_total == 15_000.0
    assert breakdown.total_recurring_over_term == 360_000.0

    # Total protection cost = 2.9M + 2.4M + 360k = 5,660,000
    assert breakdown.total_protection_cost == pytest.approx(5_660_000.0)
    assert len(breakdown.itemized_records) == 11


def test_protection_cost_toggle_disable():
    """Verify toggling off an item removes it from totals."""
    config = ProtectionCostConfig()
    config.insurance_upfront.enabled = False  # Disable 1.2M insurance

    breakdown = calculate_lease_protection(config, 48_000_000.0, 12)
    # Fixed upfront drops from 2.9M to 1.7M
    assert breakdown.fixed_upfront_total == 1_700_000.0


def test_fleet_operational_costs():
    """Verify fleet direct operating costs calculation."""
    f_cost = FleetOperationalCostConfig(
        maintenance_monthly_per_truck=350_000.0,
        tyres_repairs_monthly_reserve=200_000.0,
        parking_yard_monthly_reserve=50_000.0,
        annual_insurance_per_truck=1_200_000.0,  # 100k/mo
        admin_accounting_monthly_per_truck=50_000.0,
    )
    # Total monthly = 350k + 200k + 50k + 100k + 50k = 750,000 FCFA/mo
    assert f_cost.total_monthly_direct_operating_cost() == 750_000.0


# ===========================================================================
# Tax Engine Tests (AGENTS.md Core Rule 4 & Section 9)
# ===========================================================================

def test_statutory_vat_rate_reference():
    """Verify Cameroon 2026 General Tax Code statutory rate is 19.25%."""
    assert STATUTORY_VAT_RATE == 0.1925
    assert "2026" in DGI_GTC_2026_REFERENCE

    vat_meta = TAX_METADATA_REGISTRY["vat_rate"]
    assert vat_meta.provenance == TaxProvenance.VERIFIED_STATUTORY
    assert "19.25%" in vat_meta.legal_reference

    cit_meta = TAX_METADATA_REGISTRY["corporate_income_tax_rate"]
    assert cit_meta.provenance == TaxProvenance.INPUT_ASSUMPTION


def test_vat_calculation_and_recoverability():
    """Verify VAT calculations and recoverability toggle."""
    tax_base = 50_000_000.0

    # Non-recoverable VAT: 50M * 19.25% = 9,625,000 FCFA cost
    tax_cfg_unrec = TaxConfiguration(vat_rate=0.1925, vat_recoverable=False)
    vat_unrec = calculate_vat(tax_base, tax_cfg_unrec)
    assert vat_unrec == 50_000_000.0 * 0.1925
    assert vat_unrec == 9_625_000.0

    # Recoverable VAT: net unrecoverable cost is 0.0
    tax_cfg_rec = TaxConfiguration(vat_rate=0.1925, vat_recoverable=True)
    vat_rec = calculate_vat(tax_base, tax_cfg_rec)
    assert vat_rec == 0.0


def test_corporate_income_tax():
    """Verify Corporate Income Tax on positive profit and zero tax on losses."""
    tax_cfg = TaxConfiguration(corporate_income_tax_rate=0.30)

    # Positive taxable profit 10M -> 3M tax
    assert calculate_corporate_income_tax(10_000_000.0, tax_cfg) == 3_000_000.0

    # Zero or negative profit -> 0 tax
    assert calculate_corporate_income_tax(0.0, tax_cfg) == 0.0
    assert calculate_corporate_income_tax(-5_000_000.0, tax_cfg) == 0.0


def test_calculate_tax_impact():
    """Verify complete pre-tax vs after-tax impact calculations."""
    tax_cfg = TaxConfiguration(corporate_income_tax_rate=0.30)

    # Revenue 50M, Deductible Expenses 30M -> 20M pre-tax profit -> 6M CIT -> 14M net after-tax
    res = calculate_tax_impact(50_000_000.0, 30_000_000.0, tax_cfg)
    assert res["pre_tax_profit"] == 20_000_000.0
    assert res["corporate_income_tax"] == 6_000_000.0
    assert res["net_after_tax_profit"] == 14_000_000.0
    assert res["effective_tax_rate"] == pytest.approx(0.30)
    assert res["is_profitable"] is True


def test_tax_invalid_inputs():
    """Verify out-of-bounds tax parameters raise validation errors."""
    with pytest.raises(SimulatorValidationError):
        TaxConfiguration(vat_rate=-0.05)

    with pytest.raises(SimulatorValidationError):
        TaxConfiguration(corporate_income_tax_rate=0.85)

    with pytest.raises(SimulatorValidationError):
        calculate_vat(-1000.0, TaxConfiguration())

