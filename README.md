# Dump Truck Finance & Leasing Simulator

An interactive deterministic financial simulation web application built with Python and Streamlit.
Designed to evaluate and optimize capital allocation for financed dump-truck fleets across three strategic pathways:

1. **Direct Cash Sale (Strategy A)**: Rapid inventory turnover, immediate cash release, and markup analysis.
2. **Customer Leasing / Commercial Proposals (Strategy B)**: Dynamic deposit-driven proposal generator for 6, 12, 18, and 24-month terms ($\le 2$ years). Automatically excludes long terms for high deposits (e.g. 30M FCFA) and generates instant commercial quotes.
3. **Company Fleet Exploitation (Strategy C)**: Direct vehicle operations generating monthly operational profits with maintenance and downtime allowances.
4. **Bilingual Interface**: Full instant toggle between French (CEMAC / OHADA business terminology) and English.
5. **No-Jargon Executive Metrics**: Straightforward cash profit, immediate cash-in-hand, monthly payments, and payback horizons.

## Project Structure

```
├── AGENTS.md                  # Development principles & boundary constraints
├── README.md                  # Project overview and setup instructions
├── requirements.txt           # Python dependency specifications
├── app.py                     # Streamlit web application
├── docs/
│   └── PROGRAMMING_PLAN.md   # Detailed implementation specification V1
├── simulator/                 # Core financial logic engine (UI independent)
│   ├── __init__.py
│   ├── models.py             # Data models, validation, and types
│   ├── loan.py               # Bank loan amortization engine
│   ├── acquisition.py        # Discrete batch procurement engine
│   ├── sale.py               # Cash-sale pricing and return engine
│   ├── lease.py              # Lease installment calculation engine
│   ├── exploitation.py       # Direct exploitation cash flow engine
│   ├── costs.py              # Operating, security, and transaction costs
│   ├── taxes.py              # Configurable tax calculations
│   ├── portfolio.py          # Portfolio state and truck lifecycle management
│   ├── simulation.py         # Monthly discrete event simulation runner
│   └── metrics.py            # Financial KPIs (NPV, IRR, ROI, Payback)
└── tests/                     # Automated unit and regression test suite
    ├── __init__.py
    ├── test_loan.py
    ├── test_acquisition.py
    ├── test_sale.py
    ├── test_lease.py
    ├── test_exploitation.py
    └── test_simulation.py
```

---

## Quickstart

### Prerequisites

- Python 3.12+

### Setup

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
pytest -v
```

### Running the Web Application

```bash
streamlit run app.py
```
