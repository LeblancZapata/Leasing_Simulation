# Dump Truck Finance & Leasing Simulator (V1)

An interactive, deterministic monthly financial simulation web application built with Python and Streamlit.
Designed to evaluate and optimize capital allocation for financed dump-truck fleets across three strategic pathways:
1. **Direct Cash Sale (Strategy A)**: Rapid inventory turnover, immediate cash release, and markup analysis.
2. **Customer Leasing / Installment Finance (Strategy B)**: Structured 6, 12, 18, or 24-month payment streams with risk reserves and dynamic down payments ($\ge$ 10M FCFA).
3. **Company Fleet Exploitation (Strategy C)**: Direct vehicle operations generating monthly operational profits with maintenance and downtime allowances.

---

## Architecture & Codebase Layout

Strict separation of concerns is maintained: all financial calculation logic is encapsulated in `simulator/` and is 100% independent of Streamlit and UI code.

```
├── AGENTS.md                  # Development principles & boundary constraints
├── README.md                  # Project overview and setup instructions
├── requirements.txt           # Python dependency specifications
├── app.py                     # Streamlit web application (Tabs 1 to 6)
├── docs/
│   └── PROGRAMMING_PLAN.md   # Detailed 16-step implementation specification V1
├── simulator/                 # Core financial logic engine (UI independent)
│   ├── __init__.py           # Package exports
│   ├── primitives.py         # Currency, formatting, rate conversion, validation
│   ├── models.py             # Domain dataclasses & parameter configurations
│   ├── loan.py               # Bank loan amortization engine
│   ├── acquisition.py        # Discrete batch procurement (multiples of 5)
│   ├── sale.py               # Cash-sale pricing, carry cost, and returns
│   ├── lease.py              # Lease installment schedules, deposits, NPV/IRR
│   ├── exploitation.py       # Direct operational cash flow and payback
│   ├── costs.py              # Operating, security, and itemized legal reserves
│   ├── taxes.py              # Cameroon 2026 GTC statutory tax calculations
│   ├── portfolio.py          # Truck state machine and monthly snapshot models
│   ├── simulation.py         # Deterministic monthly discrete-event portfolio engine
│   ├── metrics.py            # Financial KPIs (ROI, NPV, IRR, DSCR, cash-on-cash)
│   └── scenarios.py          # 36-scenario matrix and preset sensitivity runner
└── tests/                     # 89 automated regression unit tests
    ├── test_smoke.py
    ├── test_primitives.py
    ├── test_loan.py
    ├── test_acquisition.py
    ├── test_sale.py
    ├── test_lease.py
    ├── test_costs_taxes.py
    ├── test_exploitation.py
    ├── test_simulation.py
    ├── test_metrics.py
    ├── test_scenarios.py
    └── test_integration.py
```

---

## Quickstart Guide

### Prerequisites
- Python 3.12+ (tested and verified on Python 3.14)
- Virtual environment (`venv`)

### 1. Installation
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Automated Regression Tests
All 89 tests verify mathematical correctness, discrete batch rules, tax calculations, and lifecycle invariants:
```bash
pytest -v
```

### 3. Launch the Interactive Web Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## Core Invariants & Business Rules

1. **Discrete Batch Purchasing**: Dump trucks are ordered strictly in multiples of 5 (5, 10, 15, 20, ...). The simulation never buys fractional trucks and waits until sufficient capital exists while preserving the user-defined safety cash reserve.
2. **Statutory Lease Down Payment**: Customer lease contracts strictly require an initial cash deposit $\ge 10,000,000\text{ FCFA}$. Any deposit below this threshold is rejected.
3. **Discrete Lease Terms**: Leases are strictly limited to 6, 12, 18, or 24 months.
4. **Deterministic Monthly Simulation**: Monthly time steps are processed sequentially:
   - Opening balances $\rightarrow$ Inflows (lease deposits, installments, exploitation cash, sales) $\rightarrow$ Protection & Operating costs $\rightarrow$ Bank debt installment $\rightarrow$ Discrete batch reinvestment $\rightarrow$ Closing balances.
5. **Strategy Recommendation Decision Rule (Section 12.1)**:
   $$\text{best\_strategy} = \arg\max(\text{risk\_adjusted\_npv})$$
   $$\text{subject to: } \text{minimum\_cash} \ge \text{required\_reserve},\; \text{lease\_deposit} \ge 10\text{M},\; \text{batch\_multiple} = 5$$
6. **Statutory Tax Provenance**: Cameroon General Tax Code (2026 CGI Art. 149) statutory VAT rate of 19.25% (17.5% base + 10% CAC) is distinctly flagged as verified statutory, while recovery rights and CIT are labeled as input assumptions.

---

## Application Layout (6 Interactive Tabs)

- **Tab 1: 🏦 Financing & Procurement**: Bank debt amortization schedule, landed truck cost presets (38M / 40M / 42M), batch procurement affordability, cash shortfall, and next batch timing.
- **Tab 2: 💰 Strategy A: Cash Sale**: Dynamic price floor, financing carry cost during inventory holding, recommended asking price, buyer offer evaluation, and market benchmark comparison.
- **Tab 3: 📄 Strategy B: Customer Leasing**: Price-first vs payment-first schedule generation, Section 9.1 itemized security toggles, early payoff analysis, and DCF NPV/IRR.
- **Tab 4: 🚜 Strategy C: Exploitation**: Monthly operational profit (2M–3M FCFA presets), downtime reduction slider, cumulative cash flows, and payback milestones.
- **Tab 5: 📊 Results & Strategy Comparison**:
  - **Strategy Decision Engine Card**: Recommended strategy banner with mathematical rationale and invariant verification.
  - **Three Comparative Strategy Cards**: Side-by-side ROI, IRR, NPV, Risk-Adjusted NPV, payback, and liquidity profiles.
  - **Risk & Liquidity Warning Center**: Real-time alerts for cash reserve breach, sub-floor pricing, DSCR debt coverage (< 1.00x critical, < 1.25x narrow), and procurement shortfalls.
  - **Monthly Portfolio Simulation**: Interactive fleet scaling, cash vs debt amortization curves, and full CSV export.
- **Tab 6: 🎯 Scenario Matrix & Sensitivity**:
  - Landed Cost presets comparison: Best (38M), Average (40M), Worst (42M).
  - Complete 36-Scenario Matrix ($3\text{ costs} \times 3\text{ rates} \times 4\text{ terms}$): Multi-select filters, summary statistics, and complete CSV dataset download.

---

## Canonical Test Scenario (Section 5.1 & 15.1)

To test the default baseline assumptions:
- **Bank Loan Amount**: 500,000,000 FCFA
- **Financing Rate**: 20% annual nominal (1.67% monthly)
- **Loan Horizon**: 36 months
- **Minimum Cash Reserve**: 20,000,000 FCFA
- **Truck Landed Cost**: 40,000,000 FCFA
- **Procurement Batch Size**: 5 trucks

**Expected Baseline Outputs**:
- Monthly Bank Payment: $\approx 18,581,789\text{ FCFA}$
- Total Debt Repayment: $\approx 668,944,402\text{ FCFA}$
- Initial Trucks Purchased: 10 trucks (2 batches of 5; 400M cost; leaving 100M unallocated capital $\ge$ 20M reserve)
- Strategy B Recommended Contract Price: $\approx 58,000,000\text{ FCFA}$ (with 10M deposit, producing 2,000,000 FCFA/mo installment over 24 months)
- Strategy C Payback: $\approx 16.0\text{ months}$ at 2.5M FCFA net profit/truck/month
