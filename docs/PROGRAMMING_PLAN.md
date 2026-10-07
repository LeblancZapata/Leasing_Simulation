# Dump Truck Finance & Leasing Simulator
## PROGRAMMING IMPLEMENTATION PLAN — V1
*A build-ready specification for Antigravity + Python + Streamlit*

### Purpose
Build an interactive simulator that decides how a financed dump-truck portfolio should allocate capital across direct cash sale, customer leasing/installment finance, and company exploitation. V1 is deterministic and monthly. It must be usable by a non-programmer through sliders, numeric inputs, tables, and charts.

**Important distinction:** This document is a programming plan: it tells the coding agent what to build, in what order, what files to create, what formulas to implement, and how to test each stage. It is not a business plan and it intentionally keeps uncertain tax/legal amounts configurable.

---

### 1. V1 Scope
Build one local web application. Do not start with a database server, authentication, deployment, mobile app, Monte Carlo, or external APIs. The first milestone is a reliable local simulator that can be tested with the family’s real assumptions.

- **Financing:** editable bank loan amount, annual rate, term, and optional bank fees.
- **Procurement:** truck landed cost with editable value plus presets 38M / 40M / 42M FCFA.
- **Batch purchasing:** trucks are ordered only in multiples of 5 (5, 10, 15, 20, …). The simulator waits until enough available cash exists for the next complete batch while preserving the required cash reserve.
- **Strategy A — cash sale:** immediate sale after acquisition/holding period.
- **Strategy B — lease/installment:** 6, 12, 18, or 24 months; initial deposit cannot be below 10M FCFA; remaining price becomes the customer repayment schedule.
- **Strategy C — exploitation:** user enters net profit per truck/month, default range 2M–3M FCFA; no reported-vs-verified-round comparison in V1.
- **Monthly portfolio simulation:** cash balance, debt balance, truck count, lease receivables, exploitation cash flow, sales proceeds, and reinvestment.
- **Dynamic pricing:** never hard-code 46M as the selling price. Calculate a recommended price from cost, financing carry, transaction costs, target return/margin, and market-price input.
- **Cost/tax layer:** configurable insurance, GPS, legal/contract, registration, taxes, customs/import costs, administration, recovery reserve, maintenance, downtime, and other expenses.
- **Decision dashboard:** compare the three strategies using net cash generated, ROI, NPV, IRR, payback, and liquidity impact.

---

### 2. What to Set Up in Antigravity Before Implementation
1. Create a clean project folder and open it.
2. Initialize Git immediately: `git init`.
3. Use Python 3.12+ and create a virtual environment: `python3 -m venv .venv`.
4. Activate it and create `requirements.txt`. Install only the V1 stack: `streamlit`, `pandas`, `numpy`, `plotly`, `numpy-financial`, `pytest`.
5. Create `AGENTS.md` in the project root. Tell the agent to implement incrementally, preserve separation between financial logic and UI, write tests before/alongside each module, and never silently invent tax/legal rates.
6. Create `docs/PROGRAMMING_PLAN.md` by copying the implementation plan.
7. Do not ask Antigravity to implement the entire simulator from this document in one pass. Give it one milestone at a time and require tests after each milestone.

#### Recommended Initial Folder
```text
dump-truck-simulator/
├── AGENTS.md
├── README.md
├── requirements.txt
├── app.py
├── docs/
│   └── PROGRAMMING_PLAN.md
├── simulator/
│   ├── __init__.py
│   ├── models.py
│   ├── loan.py
│   ├── acquisition.py
│   ├── sale.py
│   ├── lease.py
│   ├── exploitation.py
│   ├── costs.py
│   ├── taxes.py
│   ├── portfolio.py
│   ├── simulation.py
│   └── metrics.py
└── tests/
    ├── test_loan.py
    ├── test_acquisition.py
    ├── test_sale.py
    ├── test_lease.py
    ├── test_exploitation.py
    └── test_simulation.py
```

---

### 3. Technology Choice
- **Language:** Python 3.12+ (Simple financial calculations and easy maintenance)
- **UI:** Streamlit (Fast local web interface with sliders, forms, tables, and charts)
- **Calculations:** NumPy / numpy-financial (Reliable vector/math and standard financial functions)
- **Tables:** Pandas (Monthly schedules and portfolio summaries)
- **Charts:** Plotly (Interactive cash-flow and portfolio charts)
- **Persistence:** SQLite only when needed (Save named scenarios without introducing a server)
- **Testing:** pytest (Every financial formula must have regression tests)

---

### 4. Input Model and UI
The interface should have four main pages/tabs: Assumptions, Leasing, Exploitation, and Simulation Results. The assumptions panel controls global financing, procurement, and cost parameters.

#### 4.1 Financing Inputs
| Input | Default | Control |
|---|---|---|
| Bank loan amount | 500,000,000 FCFA | Number input |
| Annual financing rate | 20% | Slider, e.g. 5%–35%, step 0.5% |
| Loan term | 36 months | Slider/dropdown |
| Bank arrangement fees | 0 FCFA initially | Number input |
| Other bank/insurance financing charges | 0 FCFA initially | Number input |
| Starting company cash | 0 FCFA | Number input |
| Minimum cash reserve | User defined | Number input |

#### 4.2 Truck Cost Inputs
| Input | Default/preset | Behavior |
|---|---|---|
| Truck landed cost | 40M FCFA | Slider/number input |
| Best case | 38M FCFA | Preset button |
| Average case | 40M FCFA | Preset button |
| Worst case | 42M FCFA | Preset button |
| Batch size | 5 trucks | Dropdown: 5, 10, 15, 20, 25, … |
| Procurement/import contingency | Configurable | Separate percentage or amount |

The 38M/40M/42M figures are scenario presets, not fixed truths. The user must be able to type any other truck cost. The simulator should keep the preset buttons visible beneath the editable cost input.

---

### 5. Loan Engine
Implement a monthly amortizing loan for V1. Use the annual rate slider to derive a monthly rate. Keep bank fees separate so a quoted “all-in” rate can later be modeled accurately without rewriting the engine.

$$monthly\_rate = annual\_rate / 12$$
$$monthly\_payment = P \times r \times \frac{(1+r)^n}{(1+r)^n - 1}$$

Output a full amortization schedule: month, opening balance, payment, interest, principal, closing balance. Handle a zero-rate loan separately.

#### 5.1 Required example test
At P = 500M, annual rate = 20%, term = 36 months, the code should calculate the monthly payment and total repayment automatically. Do not hard-code the result; the test should verify the mathematical output within a small tolerance.

---

### 6. Procurement and Batch Engine
Procurement is discrete. A company cannot purchase 6.3 trucks. Orders must be complete batches.

$$affordable\_trucks = \lfloor (available\_cash - reserve) / landed\_cost \rfloor$$
$$purchasable\_trucks = \lfloor affordable\_trucks / batch\_step \rfloor \times batch\_step$$

*Example:* if the batch step is 5 and 175M is available after reserve at a 40M truck cost, the simulator can purchase 5 trucks (200M is not affordable) and must wait. When future cash receipts increase available capital enough, the next complete batch can be purchased.

- Never allow the simulation to silently buy a partial batch.
- Show the next required capital amount and the cash shortfall when a batch cannot yet be ordered.
- Show the earliest month when the next batch becomes affordable.
- Allow a user-configurable cash reserve so the algorithm does not consume every franc just because a batch becomes technically affordable.

---

### 7. Cash-Sale Pricing Engine
Do not fix 46M as the official sale price. Treat 46M as a possible market/negotiation point. The simulator should calculate a price floor and a recommended asking price.

$$price\_floor = landed\_cost + acquisition\_costs + financing\_carry + selling\_costs + risk\_reserve + minimum\_profit$$
$$recommended\_price = landed\_cost \times (1 + target\_markup) + financing\_carry + transaction\_costs + risk\_reserve$$

Starting reference for V1: with a 40M landed cost, a 20% target markup produces 48M before additional transaction/financing costs. The interface can show 46M, 47M, 48M, 49M, and 50M as comparison points, but the decision should come from the formula. A customer paying cash should receive a different effective-return assessment because capital returns immediately.

#### 7.1 Sale outputs
- Gross profit and gross margin
- Net profit after sale-related costs
- Capital tied up before sale
- Holding-period return
- Annualized return
- NPV and IRR when timing is relevant
- Capital released immediately
- Recommended minimum price
- Negotiation zone (user-defined)

---

### 8. Leasing / Installment Engine
V1 supports exactly four terms: 6, 12, 18, and 24 months. The initial deposit is dynamic but can never be less than 10M FCFA.

| Parameter | Rule |
|---|---|
| Lease term | 6, 12, 18, or 24 months only |
| Initial deposit | >= 10M FCFA |
| Customer financed balance | Total contract price - deposit |
| Payment frequency | Monthly in V1 |
| Price calculation | Dynamic from target return, costs and term |
| Early payoff | Optional V1 toggle; remaining balance recalculated |
| Late payment | Optional fee input, not mandatory in base case |
| Default | Configurable scenario in risk section |
| Asset recovery | Configurable recovery cost/time/value |

#### 8.1 Two calculation directions
- **Price-first:** user chooses deposit + term + total contract price; the program calculates the monthly installment and return.
- **Payment-capacity-first:** user chooses deposit + term + maximum monthly payment; the program calculates the maximum contract price that preserves the target return.

#### 8.2 Required leasing outputs
- Initial cash received
- Monthly installment
- Total contractual receipts
- Total financing/administrative/security costs
- Net profit
- NPV
- IRR
- Break-even payment
- Total customer cost
- Capital recovered by month
- Outstanding customer receivable
- Outstanding bank debt linked to the portfolio

---

### 9. Leasing and Exploitation Cost/Tax Engine
Never hard-code a tax or regulatory cost that may depend on the vehicle classification, taxpayer regime, import classification, transaction structure, or contract form. The 2026 Cameroon General Tax Code is published by the DGI; the current general VAT rate is 19.25%, but treatment should be modeled as configurable because recoverability and the transaction’s tax base matter.

| Cost category | Lease | Exploit | V1 treatment |
|---|---|---|---|
| VAT / indirect taxes | Yes, as applicable | Yes, as applicable | Rate + recoverability toggle |
| Corporate income tax | On taxable profit | On taxable profit | Configurable effective rate |
| Import/customs duties and port costs | Usually in landed cost | Already in truck cost | Break out, then roll into landed cost |
| Registration/title/vehicle administrative fees | Yes | Yes | Amount per truck input |
| Vehicle/road taxes | Yes, as applicable | Yes, as applicable | Annual/trimestral input |
| Insurance | Mandatory/contractual depending on activity | Mandatory/contractual | Annual premium input |
| GPS/telematics | Strongly recommended security cost | Operational control cost | Install + monthly subscription |
| Legal/contract drafting | Yes | Optional | Per-contract or annual input |
| Asset inspection/valuation | Yes | Optional | Per event |
| Recovery/default reserve | Yes | N/A or optional | % of financed receivable |
| Accounting/admin | Yes | Yes | Monthly/annual input |
| Maintenance | Usually contract-dependent | Major operating cost | Per month/truck |
| Tyres/repairs | Possible | Major operating cost | Monthly reserve |
| Downtime/yard/parking | Possible | Important | Monthly reserve |

#### 9.1 Security costs for leasing
- GPS installation
- Monthly GPS subscription
- Document/contract preparation
- Customer verification/credit assessment
- Insurance
- Vehicle inspection before handover
- Registration/title/security documentation as advised by counsel
- Collection/default reserve
- Repossession/recovery reserve
- Legal enforcement reserve
- Payment-processing/bank charges

Show a separate “Protection cost per leased truck” total.

---

### 10. Exploitation Engine
V1 intentionally does not model round-reporting discrepancies. The user's accepted business assumption is simply that a truck produces between 2M and 3M FCFA net profit per month after operating charges.

| Input | Default | Control |
|---|---|---|
| Net monthly profit/truck | 2M–3M FCFA | Slider |
| Minimum | 2M | Preset |
| Base | 2.5M | Preset |
| Maximum | 3M | Preset |
| Downtime allowance | 0% initially | Slider |
| GPS/telematics cost | Configurable | Number input |
| Other monthly overhead allocation | Configurable | Number input |

*Output:* monthly cash contribution, annual contribution, payback period on truck cost, NPV, IRR, and total cash generated over the simulation horizon.

---

### 11. Portfolio Simulation Engine
Monthly time steps processed deterministically:
1. Start with opening cash and opening bank debt.
2. Receive scheduled lease deposits/installments and exploitation cash flow.
3. Pay operating expenses and recurring protection costs.
4. Pay the bank loan installment.
5. Record sale proceeds when a truck is sold.
6. Update lease receivables and outstanding balances.
7. Compute closing cash.
8. Check whether another complete procurement batch is affordable after maintaining the cash reserve.
9. If yes, purchase exactly the largest affordable multiple of the batch step; if no, wait.
10. Record portfolio KPIs and continue to the next month.

#### 11.1 Truck lifecycle states
- AVAILABLE $\rightarrow$ LEASED $\rightarrow$ COMPLETED / DEFAULTED $\rightarrow$ RECOVERED / SOLD
- AVAILABLE $\rightarrow$ EXPLOITATION $\rightarrow$ ACTIVE / DOWNTIME
- AVAILABLE $\rightarrow$ SOLD

---

### 12. Metrics and Decision Rules
- Net profit, Gross margin, ROI, Payback period, NPV, IRR, Cash-on-cash return.
- Bank debt balance, Monthly debt service, Minimum cash balance, Available capital for next batch, Lease receivables outstanding.
- Trucks and capital invested per strategy, Cumulative cash generated.

#### 12.1 Strategy recommendation
$$\text{best\_strategy} = \arg\max(\text{risk\_adjusted\_npv})$$
$$\text{subject to: } \text{minimum\_cash} \ge \text{required\_reserve},\; \text{lease\_deposit} \ge 10\text{M},\; \text{procurement\_quantity} \pmod{\text{batch\_step}} == 0$$

---

### 13. Scenario System
Presets:
- Best: 38M FCFA
- Average: 40M FCFA
- Worst: 42M FCFA

Scenario matrix: 38/40/42M $\times$ 15%/20%/25% financing $\times$ 6/12/18/24-month lease terms.

---

### 14. Streamlit Interface Layout
- **Sidebar:** loan amount, interest-rate slider, loan term, cash reserve, truck cost slider, batch size, simulation horizon.
- **Main “Leasing” panel:** term selector, deposit input, total contract price or monthly-payment mode, security-cost toggles.
- **Main “Exploitation” panel:** net profit/truck/month slider and recurring cost inputs.
- **Main “Cash Sale” panel:** recommended price, price floor, customer offer input, holding period.
- **Results dashboard:** three strategy cards plus portfolio totals.
- **Charts:** cash balance over time, debt balance, cumulative cash generation, trucks by strategy, monthly inflows/outflows.
- **Warnings:** insufficient liquidity, price below floor, deposit below 10M, impossible batch purchase, negative cash, weak debt coverage.

---

### 15. Testing Plan
Regression test suites:
- **Loan:** Zero rate; standard loan; final balance = 0; total principal = original principal.
- **Batch:** Cannot buy partial batch; buys 5 when affordable; waits when short; preserves reserve.
- **Sale:** 38/40/42M costs; price floor; cash release timing.
- **Lease:** 6/12/18/24 months; deposit exactly 10M; deposit below 10M rejected; payment schedule totals correctly.
- **Exploitation:** 2M/2.5M/3M monthly profit; downtime reduces result; no round-reporting logic.
- **Portfolio:** Debt payment; lease cash; operating cash; reinvestment; no negative cash unless explicitly allowed.
- **Scenario:** Deterministic outputs across configurations.

---

### 16. Exact Implementation Sequence
- **Step 1 — Project skeleton:** Create the folder structure, requirements.txt, app.py, simulator package, tests package, README, and AGENTS.md. Run a trivial Streamlit page and pytest.
- **Step 2 — Financial primitives:** Implement money/percentage/date helpers and a common validation layer. Add unit tests.
- **Step 3 — Loan engine:** Implement amortization and tests. Expose loan schedule in Streamlit.
- **Step 4 — Truck acquisition + batches:** Implement truck cost presets, editable cost, batch multiple-of-5 logic, cash reserve, and next-batch calculation.
- **Step 5 — Cash sale:** Implement sale pricing, price floor, transaction costs, financing carry, cash-release timing, and return metrics.
- **Step 6 — Leasing:** Implement 6/12/18/24 terms, deposit >=10M, payment schedule, total receipts, NPV/IRR, and dynamic price/payment modes.
- **Step 7 — Cost/tax layer:** Implement configurable costs and tax parameters with clear labels for “input assumption” versus “verified statutory rate”.
- **Step 8 — Exploitation:** Implement 2M–3M net monthly profit model, downtime, and recurring protection costs.
- **Step 9 — Portfolio simulation:** Implement monthly cash/debt/truck state machine and reinvestment/batch ordering logic.
- **Step 10 — Metrics:** Implement ROI, NPV, IRR, payback, minimum cash, debt service, and capital-release metrics.
- **Step 11 — Dashboard:** Build the final Streamlit UI and charts. Keep calculation functions independent from UI code.
- **Step 12 — Scenario runner:** Add best/average/worst cost presets and comparison tables.
- **Step 13 — QA:** Run all automated tests, manual acceptance tests, and edge-case tests.
- **Step 14 — Packaging:** Create a simple README with launch instructions and test-data scenario.

