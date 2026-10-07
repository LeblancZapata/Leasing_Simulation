"""Dump Truck Finance & Leasing Simulator - Streamlit Application Entrypoint."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import simulator
from simulator import (
    FinancingAssumptions,
    ProcurementAssumptions,
    ProtectionCostConfig,
    TaxConfiguration,
    calculate_lease_protection,
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

with st.sidebar.expander("🏛️ Taxes & Fiscal Regimes (2026 GTC)", expanded=False):
    st.caption("Statutory Source: Cameroon General Tax Code 2026 (DGI)")
    vat_rate_in = st.slider(
        "VAT Rate (%) [VERIFIED STATUTORY]",
        min_value=0.0,
        max_value=30.0,
        value=19.25,
        step=0.25,
        help="Verified Statutory Rate: Art. 149 CGI (17.5% base + 10% CAC = 19.25%).",
    )
    vat_rec_in = st.checkbox(
        "VAT is Recoverable [INPUT ASSUMPTION]",
        value=False,
        help="Input Assumption: Depends on taxpayer regime (Régime Réel) and vehicle commercial usage.",
    )
    cit_rate_in = st.slider(
        "Corporate Income Tax (%) [INPUT ASSUMPTION]",
        min_value=0.0,
        max_value=40.0,
        value=30.0,
        step=1.0,
        help="Input Assumption: Standard statutory corporate income tax rate on net taxable profits.",
    )
    reg_fee_in = st.number_input(
        "Vehicle Title / Registration (FCFA) [INPUT ASSUMPTION]",
        min_value=0.0,
        value=500_000.0,
        step=50_000.0,
        format="%.0f",
    )
    road_tax_in = st.number_input(
        "Annual Axle / Road Tax (FCFA) [INPUT ASSUMPTION]",
        min_value=0.0,
        value=150_000.0,
        step=25_000.0,
        format="%.0f",
    )

tax_configuration = TaxConfiguration(
    vat_rate=vat_rate_in / 100.0,
    vat_recoverable=vat_rec_in,
    corporate_income_tax_rate=cit_rate_in / 100.0,
    registration_fees_per_truck=reg_fee_in,
    annual_road_tax=road_tax_in,
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
tab_assumptions, tab_sale, tab_leasing, tab_exploit, tab_results = st.tabs(
    [
        "🏦 Financing & Procurement",
        "💰 Strategy A: Cash Sale",
        "📄 Strategy B: Leasing",
        "🚜 Strategy C: Exploitation",
        "📊 Results & Allocation",
    ]
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


# TAB 2: Strategy A - Cash Sale Pricing Engine
with tab_sale:
    from simulator.sale import (
        evaluate_cash_sale_pricing,
        evaluate_sale_price_economics,
        generate_market_comparison_table,
    )

    st.subheader("Strategy A: Direct Cash Sale Pricing & Returns")
    st.markdown(
        "Direct immediate cash turnover per truck. Evaluates dynamic price floor, target markup, "
        "debt carry cost, and market negotiation points."
    )

    sale_col_left, sale_col_right = st.columns([1, 1])

    with sale_col_left:
        target_markup_pct = st.slider(
            "Target Markup (%)",
            min_value=5.0,
            max_value=50.0,
            value=20.0,
            step=1.0,
            help="Profit markup applied above unit landed cost (e.g. 20% on 40M yields 48M).",
        )
        holding_period = st.slider(
            "Holding Period Before Sale (Months)",
            min_value=0,
            max_value=6,
            value=1,
            step=1,
            help="Number of months capital remains tied up before cash receipt.",
        )
        customer_offer = st.number_input(
            "Customer Offer / Negotiation Price (FCFA)",
            min_value=10_000_000.0,
            max_value=100_000_000.0,
            value=46_000_000.0,
            step=500_000.0,
            format="%.0f",
            help="Candidate buyer price to evaluate against price floor and target margin.",
        )

    with sale_col_right:
        with st.expander("Sale Transaction & Risk Adjustments", expanded=False):
            selling_costs_in = st.number_input("Selling / Brokerage Costs (FCFA)", min_value=0.0, value=0.0, step=100_000.0, format="%.0f")
            trans_costs_in = st.number_input("Transaction / Delivery Costs (FCFA)", min_value=0.0, value=0.0, step=100_000.0, format="%.0f")
            risk_reserve_in = st.number_input("Risk Reserve (FCFA)", min_value=0.0, value=0.0, step=100_000.0, format="%.0f")
            min_profit_in = st.number_input("Minimum Floor Profit (FCFA)", min_value=0.0, value=0.0, step=250_000.0, format="%.0f")

    # Evaluate Pricing
    pricing_result = evaluate_cash_sale_pricing(
        landed_cost=procurement_assumptions.effective_unit_cost,
        target_markup=target_markup_pct / 100.0,
        holding_period_months=holding_period,
        annual_financing_rate=financing_assumptions.annual_financing_rate,
        selling_costs=selling_costs_in,
        transaction_costs=trans_costs_in,
        risk_reserve=risk_reserve_in,
        minimum_profit=min_profit_in,
    )

    offer_econ = evaluate_sale_price_economics(customer_offer, pricing_result)

    st.markdown("---")
    # Top Pricing Metrics
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Price Floor (Minimum)", format_fcfa(pricing_result.price_floor), help="Strict break-even threshold including carry, costs, and risk reserve")
    with m2:
        st.metric("Recommended Price", format_fcfa(pricing_result.recommended_price), help="Formula: Landed Cost * (1 + Markup) + Financing Carry + Costs + Reserve")
    with m3:
        st.metric("Customer Offer Price", format_fcfa(customer_offer), delta=f"{format_fcfa(offer_econ.price_floor_delta)} vs floor")
    with m4:
        st.metric("Net Profit per Truck", format_fcfa(offer_econ.net_profit), delta=format_pct(offer_econ.net_margin))

    # Decision alert
    if offer_econ.is_above_floor:
        st.success(
            f"✅ **Viable Offer**: The offer of **{format_fcfa(customer_offer)}** exceeds the price floor "
            f"by **{format_fcfa(offer_econ.price_floor_delta)}** with a net margin of **{format_pct(offer_econ.net_margin)}**. "
            f"Immediate capital released upon sale: **{format_fcfa(offer_econ.capital_released)}**."
        )
    else:
        st.error(
            f"⚠️ **Offer Below Floor**: The offer of **{format_fcfa(customer_offer)}** is "
            f"**{format_fcfa(abs(offer_econ.price_floor_delta))} below the price floor** of {format_fcfa(pricing_result.price_floor)}. "
            f"Accepting this price results in margin erosion or negative return."
        )

    # Returns breakdown and benchmark table
    sc1, sc2 = st.columns([1, 1])
    with sc1:
        st.markdown("##### Offer Economics Breakdown")
        econ_summary_df = pd.DataFrame([
            {"Metric": "Capital Tied Up", "Value": format_fcfa(offer_econ.capital_tied_up)},
            {"Metric": "Financing Carry", "Value": format_fcfa(pricing_result.financing_carry)},
            {"Metric": "Gross Profit", "Value": format_fcfa(offer_econ.gross_profit)},
            {"Metric": "Gross Margin", "Value": format_pct(offer_econ.gross_margin)},
            {"Metric": "Net Profit", "Value": format_fcfa(offer_econ.net_profit)},
            {"Metric": "Net Margin", "Value": format_pct(offer_econ.net_margin)},
            {"Metric": "Holding-Period Return", "Value": format_pct(offer_econ.holding_period_return)},
            {"Metric": "Annualized Return", "Value": format_pct(offer_econ.annualized_return)},
            {"Metric": "Capital Released Immediately", "Value": format_fcfa(offer_econ.capital_released)},
        ])
        st.dataframe(econ_summary_df, width="stretch", hide_index=True)

    with sc2:
        st.markdown("##### Market Benchmark Negotiation Matrix")
        df_benchmarks = generate_market_comparison_table(pricing_result)
        df_benchmarks_display = df_benchmarks.copy()
        df_benchmarks_display["Offer Price"] = df_benchmarks_display["Offer Price"].apply(format_fcfa)
        df_benchmarks_display["Gross Profit"] = df_benchmarks_display["Gross Profit"].apply(format_fcfa)
        df_benchmarks_display["Gross Margin"] = df_benchmarks_display["Gross Margin"].apply(format_pct)
        df_benchmarks_display["Net Profit"] = df_benchmarks_display["Net Profit"].apply(format_fcfa)
        df_benchmarks_display["Net Margin"] = df_benchmarks_display["Net Margin"].apply(format_pct)
        df_benchmarks_display["Holding Period Return"] = df_benchmarks_display["Holding Period Return"].apply(format_pct)
        df_benchmarks_display["Annualized Return"] = df_benchmarks_display["Annualized Return"].apply(format_pct)
        df_benchmarks_display["Margin vs Floor"] = df_benchmarks_display["Margin vs Floor"].apply(format_fcfa)
        st.dataframe(df_benchmarks_display, width="stretch", hide_index=True)


# TAB 3: Strategy B - Customer Leasing & Installment Plans
with tab_leasing:
    from simulator.lease import (
        calculate_lease_price_first,
        calculate_lease_payment_first,
        calculate_dynamic_recommended_lease_price,
        lease_schedule_to_dataframe,
    )

    st.subheader("Strategy B: Customer Leasing & Installment Finance")
    st.markdown(
        r"Structured vehicle financing for clients with mandatory initial deposit ($\ge$ 10M FCFA) "
        "and strict 6, 12, 18, or 24-month payment schedules."
    )

    lease_left, lease_right = st.columns([1, 1])

    with lease_left:
        selected_term = st.radio(
            "Lease Term (Months)",
            options=[6, 12, 18, 24],
            index=3,
            horizontal=True,
            help="V1 strictly supports 6, 12, 18, and 24-month terms.",
        )

        lease_deposit = st.number_input(
            "Initial Customer Deposit (FCFA)",
            min_value=10_000_000.0,
            max_value=60_000_000.0,
            value=10_000_000.0,
            step=1_000_000.0,
            format="%.0f",
            help="Statutory minimum initial deposit is 10M FCFA.",
        )

        calc_direction = st.radio(
            "Calculation Direction",
            options=[
                "Price-First (Target Contract Price)",
                "Payment-Capacity-First (Customer Monthly Budget)",
            ],
            help="Negotiate from desired selling contract price, or customer monthly installment capacity.",
        )

    with lease_right:
        with st.expander("🛡️ Section 9.1 Security Costs per Leased Truck", expanded=False):
            st.caption("Configurable legal, tracking, and risk reserves (all with individual on/off toggles):")
            prot_cfg = ProtectionCostConfig()
            prot_cfg.gps_installation.enabled = st.checkbox("GPS Installation (150k)", value=True)
            prot_cfg.gps_monthly_sub.enabled = st.checkbox("GPS Monthly Subscription (15k/mo)", value=True)
            prot_cfg.contract_preparation.enabled = st.checkbox("Legal Contract Preparation (250k)", value=True)
            prot_cfg.customer_credit_check.enabled = st.checkbox("Customer Credit / Background Check (100k)", value=True)
            prot_cfg.insurance_upfront.enabled = st.checkbox("Mandatory Annual Insurance (1.2M)", value=True)
            prot_cfg.pre_handover_inspection.enabled = st.checkbox("Pre-handover Technical Inspection (100k)", value=True)
            prot_cfg.legal_registration.enabled = st.checkbox("Security / Title Registration (300k)", value=True)
            prot_cfg.default_reserve.enabled = st.checkbox("Default / Collection Reserve (5% of receivable)", value=True)
            prot_cfg.repossession_reserve.enabled = st.checkbox("Repossession / Recovery Reserve (500k)", value=True)
            prot_cfg.legal_enforcement_reserve.enabled = st.checkbox("Legal Enforcement Reserve (300k)", value=True)

            discount_rate_input = st.slider(
                "Discount Rate for NPV (%)",
                min_value=5.0,
                max_value=35.0,
                value=20.0,
                step=0.5,
                help="Reference hurdle / bank rate used for net present value discounting.",
            )
            early_payoff_active = st.checkbox("Model Early Payoff Scenario", value=False)
            early_payoff_month_in = (
                st.selectbox(
                    "Early Payoff Month",
                    options=list(range(1, selected_term + 1)),
                    index=max(0, (selected_term // 2) - 1),
                )
                if early_payoff_active
                else None
            )

        # Compute initial estimated protection costs
        estimated_financed = max(0.0, 58_000_000.0 - lease_deposit)
        temp_prot = calculate_lease_protection(prot_cfg, estimated_financed, selected_term)
        upfront_protection = temp_prot.fixed_upfront_total + temp_prot.variable_amount
        monthly_protection = temp_prot.monthly_recurring_total
        st.info(f"🛡️ **Protection Cost per Leased Truck:** **{format_fcfa(temp_prot.total_protection_cost)}** ({selected_term}-mo term)")


    rec_contract_price = calculate_dynamic_recommended_lease_price(
        truck_cost=procurement_assumptions.effective_unit_cost,
        initial_deposit=lease_deposit,
        term_months=selected_term,
        target_annual_return=0.25,
        upfront_protection_costs=upfront_protection,
        monthly_costs=monthly_protection,
    )

    if calc_direction == "Price-First (Target Contract Price)":
        target_contract_price = st.number_input(
            "Total Contract Price (FCFA)",
            min_value=lease_deposit,
            max_value=120_000_000.0,
            value=float(max(58_000_000.0, rec_contract_price)),
            step=1_000_000.0,
            format="%.0f",
            help=f"Total price paid by customer (Deposit + all installments). Recommended target: {format_fcfa(rec_contract_price)}.",
        )
        lease_eval = calculate_lease_price_first(
            total_contract_price=target_contract_price,
            initial_deposit=lease_deposit,
            term_months=selected_term,
            truck_cost=procurement_assumptions.effective_unit_cost,
            upfront_protection_costs=upfront_protection,
            monthly_costs=monthly_protection,
            discount_rate=discount_rate_input / 100.0,
            early_payoff_month=early_payoff_month_in,
        )
    else:
        max_monthly_budget = st.number_input(
            "Customer Max Monthly Payment (FCFA/month)",
            min_value=500_000.0,
            max_value=10_000_000.0,
            value=2_000_000.0,
            step=100_000.0,
            format="%.0f",
            help="Maximum affordable monthly installment quoted by customer.",
        )
        lease_eval = calculate_lease_payment_first(
            max_monthly_payment=max_monthly_budget,
            initial_deposit=lease_deposit,
            term_months=selected_term,
            truck_cost=procurement_assumptions.effective_unit_cost,
            upfront_protection_costs=upfront_protection,
            monthly_costs=monthly_protection,
            discount_rate=discount_rate_input / 100.0,
            early_payoff_month=early_payoff_month_in,
        )

    st.markdown("---")
    # Leasing Key KPI Metrics
    lk1, lk2, lk3, lk4 = st.columns(4)
    with lk1:
        st.metric("Monthly Installment", format_fcfa(lease_eval.monthly_installment), help="Regular customer payment per month")
    with lk2:
        st.metric("Total Contract Price", format_fcfa(lease_eval.total_contract_price), delta=f"Financed: {format_fcfa(lease_eval.financed_balance)}")
    with lk3:
        st.metric("Net Lease Profit", format_fcfa(lease_eval.net_profit), help="Receipts minus truck cost and protection/admin costs")
    with lk4:
        st.metric("Break-Even Installment", format_fcfa(lease_eval.break_even_payment), help="Minimum monthly installment to cover all costs")

    lk5, lk6, lk7, lk8 = st.columns(4)
    with lk5:
        st.metric("Initial Cash Inflow", format_fcfa(lease_eval.initial_deposit), help="Deposit received immediately upon signing")
    with lk6:
        st.metric("NPV (Discounted Cash Flow)", format_fcfa(lease_eval.npv), help=f"NPV discounted at {discount_rate_input:.1f}% annual rate")
    with lk7:
        irr_str = format_pct(lease_eval.irr_annualized) if lease_eval.irr_annualized is not None else "N/A"
        st.metric("Annualized IRR", irr_str, help="Internal rate of return annualized across repayment timeline")
    with lk8:
        st.metric("Total Vehicle Costs", format_fcfa(lease_eval.total_costs), help="Truck acquisition + upfront & recurring protection")

    # Schedule Visual Chart & Table
    df_lease_sched = lease_schedule_to_dataframe(lease_eval)
    lchart_col, ltable_col = st.columns([1, 1])

    with lchart_col:
        st.markdown("##### Receivables & Capital Recovery Trajectory")
        if not df_lease_sched.empty:
            fig_lease = go.Figure()
            fig_lease.add_trace(
                go.Scatter(
                    x=df_lease_sched["Month"],
                    y=df_lease_sched["Closing Receivable"],
                    mode="lines+markers",
                    name="Outstanding Receivable",
                    line=dict(color="#d62728", width=3),
                )
            )
            fig_lease.add_trace(
                go.Scatter(
                    x=df_lease_sched["Month"],
                    y=df_lease_sched["Cumulative Recovered"],
                    mode="lines+markers",
                    name="Cumulative Cash Inflows",
                    line=dict(color="#2ca02c", width=3),
                )
            )
            fig_lease.update_layout(
                xaxis_title="Month",
                yaxis_title="FCFA",
                height=350,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            try:
                st.plotly_chart(fig_lease, width="stretch")
            except TypeError:
                st.plotly_chart(fig_lease, use_container_width=True)

    with ltable_col:
        st.markdown("##### Customer Repayment Schedule")
        if not df_lease_sched.empty:
            df_lease_display = df_lease_sched.copy()
            for col in ["Opening Receivable", "Installment", "Closing Receivable", "Cumulative Recovered", "Net Cash Flow"]:
                df_lease_display[col] = df_lease_display[col].apply(lambda x: f"{x:,.0f} FCFA")
            try:
                st.dataframe(df_lease_display, height=350, width="stretch")
            except TypeError:
                st.dataframe(df_lease_display, height=350, use_container_width=True)

            csv_lease = df_lease_sched.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Lease Repayment Schedule (CSV)",
                data=csv_lease,
                file_name=f"lease_schedule_{selected_term}m_{int(lease_deposit/1e6)}M_deposit.csv",
                mime="text/csv",
            )


# TAB 4: Strategy C - Direct Fleet Exploitation
with tab_exploit:
    from simulator.exploitation import (
        EXPLOITATION_PROFIT_PRESETS,
        evaluate_exploitation,
        exploitation_schedule_to_dataframe,
    )

    st.subheader("Strategy C: Direct Fleet Exploitation")
    st.markdown(
        "Direct operations producing net operational cash flow after operating charges. "
        "Evaluates downtime sensitivity, capital payback timeline, and horizon returns."
    )

    if "exploit_profit" not in st.session_state:
        st.session_state.exploit_profit = EXPLOITATION_PROFIT_PRESETS["Base"]

    exp_col1, exp_col2 = st.columns([1, 1])

    with exp_col1:
        net_profit_input = st.number_input(
            "Net Operational Profit per Truck/Month (FCFA)",
            min_value=1_000_000.0,
            max_value=6_000_000.0,
            value=float(st.session_state.exploit_profit),
            step=100_000.0,
            format="%.0f",
            help="Net profit generated per truck per active working month.",
            key="exploit_profit_in",
        )
        st.session_state.exploit_profit = net_profit_input

        st.caption("Operational Profit Presets (Section 10):")
        ep_cols = st.columns(3)
        with ep_cols[0]:
            if st.button("Min 2.0M", key="btn_exp_min"):
                st.session_state.exploit_profit = EXPLOITATION_PROFIT_PRESETS["Minimum"]
                st.rerun()
        with ep_cols[1]:
            if st.button("Base 2.5M", key="btn_exp_base"):
                st.session_state.exploit_profit = EXPLOITATION_PROFIT_PRESETS["Base"]
                st.rerun()
        with ep_cols[2]:
            if st.button("Max 3.0M", key="btn_exp_max"):
                st.session_state.exploit_profit = EXPLOITATION_PROFIT_PRESETS["Maximum"]
                st.rerun()

        downtime_pct = st.slider(
            "Downtime Allowance (%)",
            min_value=0.0,
            max_value=30.0,
            value=0.0,
            step=1.0,
            help="Operational buffer for repairs, bad weather, or driver downtime.",
        )

    with exp_col2:
        fleet_size_eval = st.number_input(
            "Operating Truck Count",
            min_value=1,
            max_value=100,
            value=max(1, initial_procurement_eval.purchasable_trucks),
            step=1,
            help="Number of dump trucks deployed in company fleet.",
        )
        with st.expander("Recurring Monitoring & Overhead Deductions", expanded=False):
            gps_monthly_exp = st.number_input(
                "GPS Telematics Cost (FCFA/truck/month)",
                min_value=0.0,
                value=15_000.0,
                step=5_000.0,
                format="%.0f",
            )
            overhead_monthly_exp = st.number_input(
                "Other Monthly Overhead Allocation (FCFA/truck/month)",
                min_value=0.0,
                value=0.0,
                step=25_000.0,
                format="%.0f",
            )
            horizon_exp = st.slider(
                "Simulation Horizon (Months)",
                min_value=12,
                max_value=60,
                value=loan_term_months,
                step=6,
                help="Horizon over which cumulative cash flow and DCF returns are evaluated.",
            )

    # Evaluate Exploitation Strategy
    exploit_result = evaluate_exploitation(
        truck_cost=procurement_assumptions.effective_unit_cost,
        net_monthly_profit_per_truck=st.session_state.exploit_profit,
        downtime_rate=downtime_pct / 100.0,
        gps_monthly_cost=gps_monthly_exp,
        other_overhead=overhead_monthly_exp,
        truck_count=fleet_size_eval,
        horizon_months=horizon_exp,
        discount_rate=financing_assumptions.annual_financing_rate,
    )

    st.markdown("---")
    # Top KPI Cards
    ek1, ek2, ek3, ek4 = st.columns(4)
    with ek1:
        st.metric(
            "Effective Cash / Truck / Month",
            format_fcfa(exploit_result.effective_monthly_cash_per_truck),
            delta=f"-{downtime_pct:.0f}% downtime" if downtime_pct > 0 else "0% downtime",
        )
    with ek2:
        st.metric(
            "Total Fleet Monthly Cash",
            format_fcfa(exploit_result.monthly_cash_fleet),
            help=f"Combined operational generation for {fleet_size_eval} trucks",
        )
    with ek3:
        payback_str = (
            f"{exploit_result.payback_period_months:.1f} mos ({exploit_result.payback_period_years:.2f} yrs)"
            if exploit_result.payback_period_months is not None
            else "N/A"
        )
        st.metric("Payback on Truck Cost", payback_str, help="Time required for net monthly cash to fully pay back the truck acquisition cost")
    with ek4:
        st.metric(
            f"Net Horizon Profit ({horizon_exp} mos)",
            format_fcfa(exploit_result.net_cash_generated),
            delta=f"Total: {format_fcfa(exploit_result.total_cash_generated)}",
        )

    ek5, ek6, ek7, ek8 = st.columns(4)
    with ek5:
        st.metric("Annual Fleet Contribution", format_fcfa(exploit_result.annual_cash_fleet), help="Total annual cash flow from active operations")
    with ek6:
        st.metric("NPV (Discounted at Loan Rate)", format_fcfa(exploit_result.npv), help=f"Discounted at {annual_rate_pct:.1f}% annual rate")
    with ek7:
        exp_irr_str = format_pct(exploit_result.irr_annualized) if exploit_result.irr_annualized is not None else "N/A"
        st.metric("Annualized IRR", exp_irr_str, help="Internal rate of return on initial fleet investment")
    with ek8:
        st.metric("Total Initial Investment", format_fcfa(procurement_assumptions.effective_unit_cost * fleet_size_eval))

    # Visual Chart & Table
    df_exp_sched = exploitation_schedule_to_dataframe(exploit_result)
    echart_col, etable_col = st.columns([1, 1])

    with echart_col:
        st.markdown("##### Cumulative Cash Generation vs Investment Payback")
        if not df_exp_sched.empty:
            total_invested = procurement_assumptions.effective_unit_cost * fleet_size_eval
            fig_exp = go.Figure()
            fig_exp.add_trace(
                go.Scatter(
                    x=df_exp_sched["Month"],
                    y=df_exp_sched["Cumulative Generated"],
                    mode="lines+markers",
                    name="Cumulative Cash Inflows",
                    line=dict(color="#2ca02c", width=3),
                )
            )
            fig_exp.add_trace(
                go.Scatter(
                    x=df_exp_sched["Month"],
                    y=[total_invested] * len(df_exp_sched),
                    mode="lines",
                    name="Initial Capital Invested",
                    line=dict(color="#d62728", width=2, dash="dash"),
                )
            )
            fig_exp.update_layout(
                xaxis_title="Month",
                yaxis_title="FCFA",
                height=350,
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            try:
                st.plotly_chart(fig_exp, width="stretch")
            except TypeError:
                st.plotly_chart(fig_exp, use_container_width=True)

    with etable_col:
        st.markdown("##### Monthly Exploitation Schedule")
        if not df_exp_sched.empty:
            df_exp_display = df_exp_sched.copy()
            for col in ["Gross Operational", "Downtime Loss", "Overhead Deductions", "Net Monthly Cash", "Cumulative Generated", "Unrecovered Capital"]:
                df_exp_display[col] = df_exp_display[col].apply(lambda x: f"{x:,.0f} FCFA")
            try:
                st.dataframe(df_exp_display, height=350, width="stretch")
            except TypeError:
                st.dataframe(df_exp_display, height=350, use_container_width=True)

            csv_exp = df_exp_sched.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Exploitation Schedule (CSV)",
                data=csv_exp,
                file_name=f"exploitation_schedule_{fleet_size_eval}_trucks_{horizon_exp}m.csv",
                mime="text/csv",
            )


# TAB 5: Portfolio Results Placeholder
with tab_results:
    st.subheader("Comparative Results & Strategy Recommendation")
    st.info("Coming in Step 9-11: Monthly portfolio simulation, discrete 5-truck batch reinvestment, and multi-strategy comparisons.")



