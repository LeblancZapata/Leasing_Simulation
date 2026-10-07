"""Dump Truck Finance & Leasing Simulator - Streamlit Application Entrypoint."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import simulator
from simulator import (
    FinancingAssumptions,
    ProcurementAssumptions,
    LANDED_COST_PRESETS,
    DEFAULT_BATCH_STEP,
    generate_loan_schedule_from_assumptions,
    schedule_to_dataframe,
    evaluate_procurement_from_assumptions,
    format_fcfa,
    format_pct,
)

st.set_page_config(
    page_title="Dump Truck Finance & Leasing Simulator",
    page_icon="🚚",
    layout="wide",
)

st.title("🚚 Dump Truck Finance & Leasing Simulator")
st.caption("Deterministic Monthly Portfolio Allocation & Strategy Decision Engine (V1)")

# ---------------------------------------------------------------------------
# Sidebar: Financing & Procurement Inputs
# ---------------------------------------------------------------------------
st.sidebar.header("🏦 Global Financing")

loan_amount = st.sidebar.number_input(
    "Bank Loan Amount (FCFA)",
    min_value=0.0,
    max_value=5_000_000_000.0,
    value=500_000_000.0,
    step=10_000_000.0,
    format="%.0f",
    help="Principal bank loan borrowed to finance initial fleet procurement.",
)

annual_rate_pct = st.sidebar.slider(
    "Annual Financing Rate (%)",
    min_value=0.0,
    max_value=35.0,
    value=20.0,
    step=0.5,
    help="Nominal annual interest rate charged by the bank.",
)

loan_term_months = st.sidebar.slider(
    "Loan Term (Months)",
    min_value=6,
    max_value=60,
    value=36,
    step=6,
    help="Bank loan repayment horizon in months.",
)

with st.sidebar.expander("Additional Bank Fees & Liquidity", expanded=False):
    bank_fees = st.number_input(
        "Bank Arrangement Fees (FCFA)",
        min_value=0.0,
        value=0.0,
        step=500_000.0,
        format="%.0f",
    )
    other_bank_charges = st.number_input(
        "Other Bank / Insurance Charges (FCFA)",
        min_value=0.0,
        value=0.0,
        step=500_000.0,
        format="%.0f",
    )
    starting_cash = st.number_input(
        "Starting Company Cash (FCFA)",
        min_value=0.0,
        value=0.0,
        step=1_000_000.0,
        format="%.0f",
    )
    min_cash_reserve = st.number_input(
        "Minimum Cash Reserve (FCFA)",
        min_value=0.0,
        value=20_000_000.0,
        step=5_000_000.0,
        format="%.0f",
        help="Safety liquidity reserve preserved before triggering new truck batch purchases.",
    )

st.sidebar.header("🚚 Truck Cost & Procurement")

if "truck_cost" not in st.session_state:
    st.session_state.truck_cost = LANDED_COST_PRESETS["Average"]

def set_preset_cost(cost: float):
    st.session_state.truck_cost = cost

truck_landed_cost = st.sidebar.number_input(
    "Truck Landed Cost (FCFA)",
    min_value=10_000_000.0,
    max_value=100_000_000.0,
    value=float(st.session_state.truck_cost),
    step=1_000_000.0,
    format="%.0f",
    help="Editable baseline landed cost per truck.",
    key="truck_cost_input",
)
st.session_state.truck_cost = truck_landed_cost

st.sidebar.caption("Landed Cost Scenario Presets:")
preset_cols = st.sidebar.columns(3)
with preset_cols[0]:
    if st.button("Best 38M", key="btn_best"):
        st.session_state.truck_cost = LANDED_COST_PRESETS["Best"]
        st.rerun()
with preset_cols[1]:
    if st.button("Avg 40M", key="btn_avg"):
        st.session_state.truck_cost = LANDED_COST_PRESETS["Average"]
        st.rerun()
with preset_cols[2]:
    if st.button("Worst 42M", key="btn_worst"):
        st.session_state.truck_cost = LANDED_COST_PRESETS["Worst"]
        st.rerun()

batch_size = st.sidebar.selectbox(
    "Procurement Batch Step (Trucks)",
    options=[5, 10, 15, 20, 25],
    index=0,
    help="Trucks are ordered strictly in complete multiples of this batch step.",
)

with st.sidebar.expander("Procurement Contingency", expanded=False):
    contingency_rate_pct = st.number_input(
        "Contingency Rate (%)",
        min_value=0.0,
        max_value=50.0,
        value=0.0,
        step=1.0,
    )
    contingency_amount = st.number_input(
        "Contingency Fixed Amount (FCFA)",
        min_value=0.0,
        value=0.0,
        step=500_000.0,
        format="%.0f",
    )

# ---------------------------------------------------------------------------
# Instantiate Domain Assumptions
# ---------------------------------------------------------------------------
financing_assumptions = FinancingAssumptions(
    bank_loan_amount=loan_amount,
    annual_financing_rate=annual_rate_pct / 100.0,
    loan_term_months=loan_term_months,
    bank_arrangement_fees=bank_fees,
    other_bank_charges=other_bank_charges,
    starting_cash=starting_cash,
    min_cash_reserve=min_cash_reserve,
)

procurement_assumptions = ProcurementAssumptions(
    landed_cost=st.session_state.truck_cost,
    batch_step=batch_size,
    contingency_rate=contingency_rate_pct / 100.0,
    contingency_amount=contingency_amount,
)

# ---------------------------------------------------------------------------
# Loan Schedule Generation
# ---------------------------------------------------------------------------
loan_schedule = generate_loan_schedule_from_assumptions(financing_assumptions)
df_schedule = schedule_to_dataframe(loan_schedule)

# Initial available cash after upfront fees
net_initial_loan_proceeds = max(0.0, loan_amount - bank_fees - other_bank_charges)
initial_available_cash = starting_cash + net_initial_loan_proceeds
initial_procurement_eval = evaluate_procurement_from_assumptions(
    available_cash=initial_available_cash,
    financing=financing_assumptions,
    procurement=procurement_assumptions,
)

# ---------------------------------------------------------------------------
# Main Tabs
# ---------------------------------------------------------------------------
tab_assumptions, tab_leasing, tab_exploit, tab_results = st.tabs(
    ["🏦 Financing & Procurement", "📄 Leasing / Installment", "🚜 Exploitation", "📊 Results & Allocation"]
)

# TAB 1: Assumptions, Loan Schedule & Batch Procurement
with tab_assumptions:
    st.subheader("1. Bank Debt & Amortization Schedule")
    st.markdown(
        f"Loan terms: **{format_fcfa(loan_amount)}** at **{annual_rate_pct:.1f}% annual rate** "
        f"over **{loan_term_months} months** (Monthly rate: {format_pct(financing_assumptions.monthly_interest_rate, 4)})."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Monthly Debt Service",
            format_fcfa(loan_schedule.monthly_payment),
            help="Fixed monthly annuity (Principal + Interest)",
        )
    with col2:
        st.metric(
            "Total Interest Repayment",
            format_fcfa(loan_schedule.total_interest),
            help="Cumulative interest paid over full term",
        )
    with col3:
        st.metric(
            "Total Cash Repaid",
            format_fcfa(loan_schedule.total_payment),
            help="Total debt service over the entire loan horizon",
        )
    with col4:
        all_in_initial_fees = bank_fees + other_bank_charges
        st.metric(
            "Effective Upfront Fees",
            format_fcfa(all_in_initial_fees),
            help="Total upfront arrangement and bank charges",
        )

    # Visual Chart & Amortization Table
    col_chart, col_table = st.columns([1, 1])

    with col_chart:
        st.markdown("##### Debt Amortization Trajectory")
        if not df_schedule.empty:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_schedule["Month"],
                    y=df_schedule["Closing Balance"],
                    mode="lines+markers",
                    name="Remaining Principal",
                    line=dict(color="#1f77b4", width=3),
                )
            )
            fig.add_trace(
                go.Bar(
                    x=df_schedule["Month"],
                    y=df_schedule["Principal"],
                    name="Principal Repaid",
                    marker_color="#2ca02c",
                    opacity=0.6,
                )
            )
            fig.add_trace(
                go.Bar(
                    x=df_schedule["Month"],
                    y=df_schedule["Interest"],
                    name="Interest Paid",
                    marker_color="#d62728",
                    opacity=0.6,
                )
            )
            fig.update_layout(
                barmode="stack",
                xaxis_title="Month",
                yaxis_title="FCFA",
                height=350,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            try:
                st.plotly_chart(fig, width="stretch")
            except TypeError:
                st.plotly_chart(fig, use_container_width=True)

    with col_table:
        st.markdown("##### Monthly Amortization Table")
        if not df_schedule.empty:
            df_display = df_schedule.copy()
            for col in ["Opening Balance", "Payment", "Interest", "Principal", "Closing Balance"]:
                df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f} FCFA")
            try:
                st.dataframe(df_display, height=350, width="stretch")
            except TypeError:
                st.dataframe(df_display, height=350, use_container_width=True)

            csv = df_schedule.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Amortization Schedule (CSV)",
                data=csv,
                file_name=f"loan_schedule_{int(loan_amount/1e6)}M_{int(annual_rate_pct)}pct_{loan_term_months}m.csv",
                mime="text/csv",
            )

    st.divider()

    # SECTION 2: Discrete Batch Procurement Engine Evaluation
    st.subheader("2. Discrete Batch Procurement Affordability (Month 0)")
    st.markdown(
        f"Unit Landed Cost: **{format_fcfa(procurement_assumptions.effective_unit_cost)}** | "
        f"Batch Ordering Step: **Multiples of {batch_size} trucks** | "
        f"Mandatory Cash Reserve: **{format_fcfa(min_cash_reserve)}**"
    )

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    with b_col1:
        st.metric(
            "Purchasable Trucks",
            f"{initial_procurement_eval.purchasable_trucks} trucks",
            delta=f"Raw affordable: {initial_procurement_eval.affordable_trucks_raw}",
            help=f"Strictly rounded down to the nearest multiple of {batch_size}. Partial batches are never ordered.",
        )
    with b_col2:
        st.metric(
            "Total Capital Invested",
            format_fcfa(initial_procurement_eval.total_batch_cost),
            help="Total acquisition expenditure for the complete batch.",
        )
    with b_col3:
        st.metric(
            "Cash Balance After Purchase",
            format_fcfa(initial_procurement_eval.remaining_cash),
            delta=f"{format_fcfa(initial_procurement_eval.unallocated_cash_after_reserve)} above reserve",
            help="Remaining cash buffer preserving the required reserve.",
        )
    with b_col4:
        st.metric(
            f"Next Batch ({initial_procurement_eval.next_batch_trucks} trucks) Shortfall",
            format_fcfa(initial_procurement_eval.cash_shortfall),
            help=f"Capital required to afford the next complete batch of {batch_size} trucks while preserving the cash reserve.",
        )

    if not initial_procurement_eval.is_batch_affordable:
        st.warning(
            f"⚠️ Insufficient capital to acquire an initial batch of {batch_size} trucks while maintaining "
            f"the {format_fcfa(min_cash_reserve)} cash reserve. "
            f"Capital shortfall: {format_fcfa(initial_procurement_eval.cash_shortfall)}."
        )
    elif initial_procurement_eval.affordable_trucks_raw > initial_procurement_eval.purchasable_trucks:
        unpurchased_fraction = initial_procurement_eval.affordable_trucks_raw - initial_procurement_eval.purchasable_trucks
        st.info(
            f"ℹ️ Discrete Batch Rule Applied: Capital is technically sufficient for {initial_procurement_eval.affordable_trucks_raw} trucks, "
            f"but orders are restricted to complete multiples of {batch_size}. "
            f"Acquiring {initial_procurement_eval.purchasable_trucks} trucks; {unpurchased_fraction} partial truck capacity "
            f"({format_fcfa(initial_procurement_eval.unallocated_cash_after_reserve)}) is held in cash waiting for the next full batch."
        )


# Placeholder tabs for future steps
with tab_leasing:
    st.subheader("Strategy B: Leasing & Installment Plans")
    st.info("Coming in Step 6: Dynamic lease terms (6, 12, 18, 24 months), deposits (>=10M FCFA), and installment pricing.")

with tab_exploit:
    st.subheader("Strategy C: Direct Fleet Exploitation")
    st.info("Coming in Step 8: Monthly profit models (2M - 3M FCFA/month), downtime allowance, and protection costs.")

with tab_results:
    st.subheader("Comparative Results & Strategy Recommendation")
    st.info("Coming in Step 9-11: Monthly portfolio simulation, discrete 5-truck batch reinvestment, and multi-strategy comparisons.")
