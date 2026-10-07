# AGENTS.md - Developer & Agent Guidelines

## Dump Truck Finance & Leasing Simulator (V1)

### Core Rules & Working Principles
1. **Implement Incrementally**: Build one milestone at a time as outlined in `docs/PROGRAMMING_PLAN.md`. Finish and test each step thoroughly before starting the next.
2. **Preserve Separation of Concerns**: Strict boundary between financial logic (`simulator/`) and user interface (`app.py`). Calculation functions must never depend on Streamlit or UI elements.
3. **Test-First / Test-Driven**: Write tests before or alongside each financial module. Every financial formula must have automated unit tests verifying mathematical correctness against expected calculations.
4. **No Speculative Tax or Legal Rates**: Never silently invent tax or legal rates. All taxes, fees, and regulatory costs must be explicitly configurable by the user, with clear distinctions between input assumptions and verified statutory references.
5. **Reproducibility & Determinism**: All portfolio simulation logic is deterministic and monthly. Time steps must be processed in a predictable order.
6. **No Unplanned Scope Creep**: Strictly respect V1 boundaries (no external APIs, no live bank/tax APIs, no auth, no Monte Carlo in V1).

