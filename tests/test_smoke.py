"""Smoke test verifying project setup and imports."""
import simulator
from simulator.models import FinancingAssumptions


def test_smoke_package_import():
    assert simulator.__version__ == "1.0.0"
    config = FinancingAssumptions()
    assert config.bank_loan_amount == 500_000_000.0
