"""Dump Truck Finance & Leasing Simulator - Streamlit Application.

Structured tabbed interface (ancient design):
- No sidebar navigation area (sidebar strictly for global parameters).
- No comparison of different paths (removed strategy comparison/ranking).
- Core operational tabs:
  1. 🏦 Financing & Fleet Procurement
  2. 📄 Client Leasing & Dynamic Proposal Generator
  3. 🚜 Fleet Operations & Exploitation
  4. 💰 Direct Cash Sale
  5. 🎯 Scenario Matrix & Sensitivity
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Optional, List, Dict, Any

from simulator import (
    FinancingAssumptions,
    ProcurementAssumptions,
    CashSaleAssumptions,
    LeaseAssumptions,
    ExploitationAssumptions,
    ProtectionCostConfig,
    TaxConfig,
    generate_loan_schedule_from_assumptions,
    schedule_to_dataframe,
    evaluate_procurement_from_assumptions,
    format_fcfa,
    format_pct,
    generate_client_lease_options,
    ClientLeaseOption,
    run_scenario_matrix,
    run_preset_comparison,
)
from simulator.sale import (
    evaluate_cash_sale_pricing,
    evaluate_sale_price_economics,
    generate_market_comparison_table,
)
from simulator.exploitation import (
    evaluate_exploitation,
    exploitation_schedule_to_dataframe,
    EXPLOITATION_PROFIT_PRESETS,
)

# ---------------------------------------------------------------------------
# Streamlit Application Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Simulateur Financier : Bennes & Leasing",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Chart Styling Utility
# ---------------------------------------------------------------------------
def apply_chart_style(fig: go.Figure, title: str = "", height: int = 370) -> go.Figure:
    """Apply clean, high-contrast aesthetic to Plotly figures."""
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=14, color="#0F172A", family="Inter, system-ui, sans-serif"),
        ),
        font=dict(family="Inter, system-ui, sans-serif", size=11, color="#334155"),
        height=height,
        margin=dict(l=25, r=20, t=45, b=25),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.8)",
        ),
        plot_bgcolor="rgba(248,250,252,0.7)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0", zeroline=False),
    )
    return fig


# ---------------------------------------------------------------------------
# Sidebar: Global Parameters (No Navigation Area)
# ---------------------------------------------------------------------------
with st.sidebar:
    # 1. Language Toggle
    lang_choice = st.radio(
        "🌐 Langue / Language",
        options=["Français 🇫🇷", "English 🇬🇧"],
        horizontal=True,
    )
    lang = "fr" if "Français" in lang_choice else "en"

    st.markdown("---")
    st.markdown("### 🏦 1. Financement Bancaire" if lang == "fr" else "### 🏦 1. Bank Financing")

    loan_amount = st.number_input(
        "Montant Emprunté à la Banque (FCFA)" if lang == "fr" else "Bank Loan Amount (FCFA)",
        min_value=0.0,
        max_value=5_000_000_000.0,
        value=500_000_000.0,
        step=20_000_000.0,
        format="%.0f",
        help="Montant principal emprunté à la banque pour financer les bennes." if lang == "fr" else "Principal bank loan borrowed to finance fleet.",
    )

    annual_rate_pct = st.number_input(
        "Taux d'Intérêt Annuel Banque (%/an)" if lang == "fr" else "Annual Bank Interest Rate (%/yr)",
        min_value=0.0,
        max_value=30.0,
        value=15.0,
        step=0.5,
        format="%.1f",
        help="Taux d'intérêt débiteur fixé à 15%/an par la banque (soit 1,25% par mois)." if lang == "fr" else "Bank interest rate fixed at 15%/yr (1.25%/month).",
    )

    bank_loan_years = st.slider(
        "Durée du Prêt Bancaire (Années)" if lang == "fr" else "Bank Loan Duration (Years)",
        min_value=1,
        max_value=5,
        value=3,
        step=1,
        help="Nombre d'années pour rembourser le crédit bancaire (ex: 3 ans = 36 mois)." if lang == "fr" else "Loan repayment term in years.",
    )
    loan_term_months = bank_loan_years * 12

    min_cash_reserve = st.number_input(
        "Réserve de Sécurité en Banque (FCFA)" if lang == "fr" else "Minimum Safety Reserve (FCFA)",
        min_value=0.0,
        value=50_000_000.0,
        step=5_000_000.0,
        format="%.0f",
        help="Trésorerie intouchable gardée en banque pour parer aux aléas." if lang == "fr" else "Safety cash buffer preserved in bank account.",
    )

    with st.expander("Frais de dossier & Trésorerie propre" if lang == "fr" else "Bank fees & Starting Cash", expanded=False):
        bank_fees = st.number_input("Frais de Dossier Bancaire (FCFA)", min_value=0.0, value=0.0, step=500_000.0, format="%.0f")
        starting_cash = st.number_input("Trésorerie Initiale Propre (FCFA)", min_value=0.0, value=0.0, step=1_000_000.0, format="%.0f")

    st.markdown("---")
    st.markdown("### 🚚 2. Achat des Bennes" if lang == "fr" else "### 🚚 2. Truck Procurement")

    cost_preset = st.segmented_control(
        "Hypothèse Coût Benne",
        options=["38M FCFA", "40M FCFA", "42M FCFA"],
        default="40M FCFA",
        label_visibility="collapsed",
    )
    default_cost = 40_000_000.0
    if cost_preset == "38M FCFA":
        default_cost = 38_000_000.0
    elif cost_preset == "42M FCFA":
        default_cost = 42_000_000.0

    truck_landed_cost = st.number_input(
        "Prix d'Achat Réel par Benne (FCFA)" if lang == "fr" else "Truck Landed Cost (FCFA)",
        min_value=10_000_000.0,
        max_value=100_000_000.0,
        value=default_cost,
        step=1_000_000.0,
        format="%.0f",
        help="Coût de revient rendu port/parc par benne neuve." if lang == "fr" else "All-in acquisition cost per truck.",
    )

    market_sale_price = st.number_input(
        "Prix de Vente Marché Local (FCFA)" if lang == "fr" else "Local Market Selling Price (FCFA)",
        min_value=20_000_000.0,
        max_value=100_000_000.0,
        value=46_000_000.0,
        step=1_000_000.0,
        format="%.0f",
        help="Prix de vente d'un camion sur le marché local (fixé à 46 000 000 FCFA). Sert de prix plancher pour toute vente ou leasing."
        if lang == "fr"
        else "Local market selling price per truck (fixed at 46,000,000 FCFA). Benchmark floor for all cash sales or leases.",
    )
    sale_markup_pct = max(0.0, ((market_sale_price - truck_landed_cost) / truck_landed_cost) * 100.0)

    net_procurement_cash = max(0.0, (starting_cash + loan_amount - bank_fees) - min_cash_reserve)
    affordable_trucks_calc = int(net_procurement_cash // truck_landed_cost) if truck_landed_cost > 0 else 5
    default_truck_count = max(5, affordable_trucks_calc)

    truck_count_input = st.number_input(
        "Nombre de Bennes Achetées (5 ou plus)" if lang == "fr" else "Number of Trucks Purchased (5 or more)",
        min_value=5,
        max_value=100,
        value=default_truck_count,
        step=1,
        help="La flotte minimale est de 5 bennes. Vous pouvez commander n'importe quel nombre : 5, 6, 7, 8, 10, 11, etc."
        if lang == "fr"
        else "Minimum fleet size is 5 trucks. You can purchase any number: 5, 6, 7, 8, 10, 11, etc.",
    )

    st.markdown("---")
    st.markdown("### ⚙️ 3. Paramètres Exploitation" if lang == "fr" else "### ⚙️ 3. Operations Parameters")

    exploit_monthly_profit = st.number_input(
        "Bénéfice Net Estimé / Benne / Mois (FCFA)" if lang == "fr" else "Est. Net Profit / Truck / Month (FCFA)",
        min_value=500_000.0,
        max_value=10_000_000.0,
        value=3_000_000.0,
        step=250_000.0,
        format="%.0f",
        help="Gain net moyen d'un camion benne en exploitation (après carburant, chauffeur et frais de route)."
        if lang == "fr"
        else "Average net profit generated per truck per active working month.",
    )

    downtime_pct = st.slider(
        "Taux d'Indisponibilité / Pannes (%)" if lang == "fr" else "Downtime / Breakdown Rate (%)",
        min_value=0.0,
        max_value=30.0,
        value=10.0,
        step=1.0,
        help="Pourcentage moyen de temps perdu pour maintenance, pannes ou intempéries." if lang == "fr" else "Operational allowance for repairs or bad weather.",
    )


# ---------------------------------------------------------------------------
# Core Object Instantiations
# ---------------------------------------------------------------------------
financing_assumptions = FinancingAssumptions(
    bank_loan_amount=loan_amount,
    annual_financing_rate=annual_rate_pct / 100.0,
    loan_term_months=loan_term_months,
    bank_arrangement_fees=bank_fees,
    other_bank_charges=0.0,
    starting_cash=starting_cash,
    min_cash_reserve=min_cash_reserve,
)

procurement_assumptions = ProcurementAssumptions(
    landed_cost=truck_landed_cost,
    batch_step=1,
)

exploitation_assumptions = ExploitationAssumptions(
    net_monthly_profit_per_truck=exploit_monthly_profit,
    downtime_allowance_rate=downtime_pct / 100.0,
)

cash_sale_assumptions = CashSaleAssumptions(
    target_markup=sale_markup_pct / 100.0,
    holding_period_months=1,
)

lease_assumptions = LeaseAssumptions(
    term_months=24,
    initial_deposit=12_000_000.0,
    target_annual_return=financing_assumptions.annual_financing_rate,
)

# Loan Schedule Pre-calculation
loan_schedule = generate_loan_schedule_from_assumptions(financing_assumptions)
df_schedule = schedule_to_dataframe(loan_schedule)

# Initial Procurement Evaluation (Month 0)
net_loan_proceeds = max(0.0, loan_amount - bank_fees)
initial_available_cash = starting_cash + net_loan_proceeds
initial_procurement_eval = evaluate_procurement_from_assumptions(
    available_cash=initial_available_cash,
    financing=financing_assumptions,
    procurement=procurement_assumptions,
)


# ---------------------------------------------------------------------------
# Main App Header
# ---------------------------------------------------------------------------
st.title(
    "🚚 Simulateur Financier : Bennes & Leasing"
    if lang == "fr"
    else "🚚 Dump Truck Finance & Leasing Simulator"
)
st.caption(
    "Modèle déterministe d'aide à la décision : Crédit bancaire, tarification crédit-bail et exploitation de flotte."
    if lang == "fr"
    else "Deterministic strategic decision engine: Bank debt, customer leasing pricing, and fleet operations."
)


# ---------------------------------------------------------------------------
# Ancient Tabbed Design (Without Navigation Area & Without Comparing Paths)
# ---------------------------------------------------------------------------
tab_titles = (
    [
        "🏦 Financement & Achat",
        "📄 Crédit-Bail / Leasing",
        "🚜 Exploitation Flotte",
        "💰 Vente Comptant",
        "🎯 Matrice des Scénarios",
    ]
    if lang == "fr"
    else [
        "🏦 Bank Financing & Fleet",
        "📄 Customer Leasing",
        "🚜 Fleet Exploitation",
        "💰 Direct Cash Sale",
        "🎯 Scenario Matrix",
    ]
)

tab_finance, tab_leasing, tab_exploit, tab_sale, tab_scenarios = st.tabs(tab_titles)


# ===========================================================================
# TAB 1: BANK FINANCING & BATCH PROCUREMENT
# ===========================================================================
with tab_finance:
    st.subheader(
        "1. Crédit Bancaire & Tableau d'Amortissement"
        if lang == "fr"
        else "1. Bank Debt & Amortization Schedule"
    )
    st.markdown(
        f"Emprunt bancaire : **{format_fcfa(loan_amount)}** au taux de **{annual_rate_pct:.1f}% / an** "
        f"sur **{bank_loan_years} an(s) ({loan_term_months} mois)**. Mensualité constante (taux mensuel : {annual_rate_pct/12.0:.2f}%)."
        if lang == "fr"
        else f"Bank loan: **{format_fcfa(loan_amount)}** at **{annual_rate_pct:.1f}% annual rate** "
        f"over **{bank_loan_years} year(s) ({loan_term_months} months)**. Fixed monthly annuity ({annual_rate_pct/12.0:.2f}%/month)."
    )

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        st.metric(
            "Traite Bancaire Mensuelle" if lang == "fr" else "Monthly Debt Service",
            format_fcfa(loan_schedule.monthly_payment),
            help="Mensualité fixe constante remboursée à la banque (Principal + Intérêts).",
            border=True,
        )
    with f_col2:
        st.metric(
            "Total Intérêts Remboursés" if lang == "fr" else "Total Interest Paid",
            format_fcfa(loan_schedule.total_interest),
            help="Coût total des intérêts payés à la banque sur toute la durée du crédit.",
            border=True,
        )
    with f_col3:
        st.metric(
            "Total Décaissé à la Banque" if lang == "fr" else "Total Cash Repaid",
            format_fcfa(loan_schedule.total_payment),
            help="Principal emprunté + total des intérêts remboursés.",
            border=True,
        )
    with f_col4:
        st.metric(
            "Réserve de Sécurité" if lang == "fr" else "Safety Cash Reserve",
            format_fcfa(min_cash_reserve),
            help="Trésorerie intouchable gardée en banque pour sécurité.",
            border=True,
        )

    # Debt Trajectory Chart & Amortization Table
    f_chart_col, f_table_col = st.columns([1, 1])

    with f_chart_col:
        st.markdown("##### 📈 Trajectoire d'Amortissement de la Dette" if lang == "fr" else "##### 📈 Debt Amortization Trajectory")
        if not df_schedule.empty:
            fig_debt = go.Figure()
            fig_debt.add_trace(
                go.Scatter(
                    x=df_schedule["Month"],
                    y=df_schedule["Closing Balance"],
                    mode="lines+markers",
                    name="Capital Restant Dû" if lang == "fr" else "Remaining Principal",
                    line=dict(color="#2563EB", width=3),
                )
            )
            fig_debt.add_trace(
                go.Bar(
                    x=df_schedule["Month"],
                    y=df_schedule["Principal"],
                    name="Principal Amorti" if lang == "fr" else "Principal Repaid",
                    marker_color="#16A34A",
                    opacity=0.7,
                )
            )
            fig_debt.add_trace(
                go.Bar(
                    x=df_schedule["Month"],
                    y=df_schedule["Interest"],
                    name="Intérêts Payés" if lang == "fr" else "Interest Paid",
                    marker_color="#DC2626",
                    opacity=0.7,
                )
            )
            fig_debt.update_layout(barmode="stack", xaxis_title="Mois", yaxis_title="FCFA")
            apply_chart_style(fig_debt, title="Évolution Mensuelle du Remboursement de la Dette", height=340)
            st.plotly_chart(fig_debt, width="stretch")

    with f_table_col:
        st.markdown("##### 📋 Tableau d'Amortissement Mensuel" if lang == "fr" else "##### 📋 Monthly Amortization Table")
        if not df_schedule.empty:
            df_sched_disp = df_schedule.copy()
            for col in ["Opening Balance", "Payment", "Interest", "Principal", "Closing Balance"]:
                df_sched_disp[col] = df_sched_disp[col].apply(format_fcfa)
            st.dataframe(df_sched_disp, height=290, width="stretch", hide_index=True)

            st.download_button(
                "📥 Télécharger l'Échéancier Bancaire (CSV)" if lang == "fr" else "📥 Download Loan Schedule (CSV)",
                data=df_schedule.to_csv(index=False).encode("utf-8"),
                file_name=f"echeancier_pret_{int(loan_amount/1e6)}M_{int(annual_rate_pct)}pct_{loan_term_months}mois.csv",
                mime="text/csv",
            )

    st.markdown("---")

    # Section 2: Fleet Procurement
    st.subheader(
        "2. Achat de la Flotte de Bennes (Commande de 5 Bennes ou Plus au Mois 0)"
        if lang == "fr"
        else "2. Fleet Procurement (5 or More Trucks at Month 0)"
    )
    total_batch_cost = truck_count_input * procurement_assumptions.effective_unit_cost
    remaining_cash = initial_available_cash - total_batch_cost
    cash_shortfall = max(0.0, (total_batch_cost + min_cash_reserve) - initial_available_cash)
    is_affordable = total_batch_cost + min_cash_reserve <= initial_available_cash
    max_affordable_trucks = int(max(0.0, initial_available_cash - min_cash_reserve) // procurement_assumptions.effective_unit_cost)

    st.markdown(
        f"Prix d'achat réel par benne : **{format_fcfa(procurement_assumptions.effective_unit_cost)}** | "
        f"Commande configurée : **{truck_count_input} bennes** (Minimum : 5) | "
        f"Réserve de trésorerie préservée : **{format_fcfa(min_cash_reserve)}**"
        if lang == "fr"
        else f"Landed cost per truck: **{format_fcfa(procurement_assumptions.effective_unit_cost)}** | "
        f"Configured order: **{truck_count_input} trucks** (Min: 5) | "
        f"Preserved reserve: **{format_fcfa(min_cash_reserve)}**"
    )

    p_col1, p_col2, p_col3, p_col4 = st.columns(4)
    with p_col1:
        st.metric(
            "Bennes Achetées" if lang == "fr" else "Purchased Trucks",
            f"{truck_count_input} bennes",
            f"Capacité max : {max_affordable_trucks} bennes",
            help="Nombre de bennes achetées (minimum 5, peut être 6, 7, 8, 10, 11...).",
            border=True,
        )
    with p_col2:
        st.metric(
            "Capital Total Investi" if lang == "fr" else "Total Capital Invested",
            format_fcfa(total_batch_cost),
            help="Montant total déboursé pour acquérir les camions.",
            border=True,
        )
    with p_col3:
        st.metric(
            "Trésorerie Restante Après Achat" if lang == "fr" else "Cash Left After Purchase",
            format_fcfa(remaining_cash),
            f"+{format_fcfa(max(0.0, remaining_cash - min_cash_reserve))} au-dessus de la réserve" if is_affordable else "⚠️ Sous la réserve",
            help="Solde de trésorerie disponible en banque après l'achat du lot.",
            border=True,
        )
    with p_col4:
        next_truck_cost = procurement_assumptions.effective_unit_cost
        st.metric(
            "Coût Benne Suivante (+1 benne)" if lang == "fr" else "Cost for +1 More Truck",
            format_fcfa(next_truck_cost),
            help="Capital nécessaire pour acheter 1 benne supplémentaire.",
            border=True,
        )

    if not is_affordable:
        st.warning(
            f"⚠️ Capital insuffisant pour financer {truck_count_input} bennes tout en conservant "
            f"la réserve de {format_fcfa(min_cash_reserve)}. Manquant : **{format_fcfa(cash_shortfall)}**. "
            f"(Votre budget actuel permet d'acheter au maximum **{max_affordable_trucks} bennes**)."
            if lang == "fr"
            else f"⚠️ Insufficient capital to acquire {truck_count_input} trucks preserving reserve. Shortfall: {format_fcfa(cash_shortfall)}."
        )
    else:
        st.success(
            f"✅ **Financement Validé :** Vous achetez **{truck_count_input} bennes** pour un total de **{format_fcfa(total_batch_cost)}**. "
            f"Il vous reste **{format_fcfa(remaining_cash)}** en banque, préservant intégralement votre réserve de sécurité de {format_fcfa(min_cash_reserve)}."
            if lang == "fr"
            else f"✅ **Funding Approved:** Purchasing {truck_count_input} trucks for {format_fcfa(total_batch_cost)}."
        )


# ===========================================================================
# TAB 2: CUSTOMER LEASING & DYNAMIC PROPOSAL GENERATOR
# ===========================================================================
with tab_leasing:
    st.subheader(
        "📄 Crédit-Bail / Leasing : Offres Clients & Barème Commercial"
        if lang == "fr"
        else "📄 Customer Leasing: Client Proposals & Dynamic Pricing"
    )
    st.markdown(
        "Saisissez ce que le client propose comme apport initial (acompte). "
        "Le système calcule immédiatement les **durées réalistes possibles** (6, 12, 18 ou 24 mois, maximum 2 ans) adaptées à cet apport."
        if lang == "fr"
        else "Enter the customer's proposed initial down payment. "
        "The engine calculates realistic terms (6, 12, 18, 24 months, strictly ≤ 2 years) tailored to that deposit."
    )

    l_in_c1, l_in_c2 = st.columns([2, 3])
    with l_in_c1:
        with st.container(border=True):
            st.markdown("#### Apport & Taux Commercial" if lang == "fr" else "#### Down Payment & Rate")
            client_deposit_in = st.number_input(
                "Apport initial versé par le client (FCFA) :" if lang == "fr" else "Initial deposit provided by client (FCFA):",
                min_value=10_000_000.0,
                max_value=80_000_000.0,
                value=10_000_000.0,
                step=1_000_000.0,
                format="%.0f",
                help="Statutairement, l'apport initial ne peut pas être inférieur à 10 000 000 FCFA.",
            )

            st.markdown("**Raccourcis rapides :**" if lang == "fr" else "**Quick shortcuts:**")
            quick_chips = st.segmented_control(
                "Montants typiques",
                options=["10M FCFA", "12M FCFA", "15M FCFA", "20M FCFA", "25M FCFA", "30M FCFA"],
                default="10M FCFA" if client_deposit_in == 10_000_000.0 else None,
                label_visibility="collapsed",
            )
            if quick_chips:
                val_num = float(quick_chips.replace("M FCFA", "")) * 1_000_000.0
                if val_num != client_deposit_in:
                    client_deposit_in = val_num

            commercial_lease_rate_pct = st.number_input(
                "Taux d'intérêt commercial crédit-bail (% / an) :" if lang == "fr" else "Commercial Leasing Annual Rate (% / yr):",
                min_value=10.0,
                max_value=60.0,
                value=26.39,
                step=0.1,
                format="%.2f",
                help="Taux annuel appliqué sur le capital restant dû du camion (prix comptant - acompte). Calibré à 26.39%/an pour atteindre exactement 65 000 000 FCFA de contrat total (25M de bénéfice net) pour 10M d'acompte sur 24 mois."
                if lang == "fr"
                else "Annual commercial rate applied to financed balance. Calibrated to 26.39%/yr to yield exactly 65M total contract (25M net profit) for 10M deposit over 24 months.",
            )

    with l_in_c2:
        with st.container(border=True):
            st.markdown("#### Règle de Décision & Rentabilité Optimale" if lang == "fr" else "#### Commercial Decision Rule & Profitability")
            if client_deposit_in >= 28_000_000.0:
                st.warning(
                    f"💡 **Apport Élevé ({format_fcfa(client_deposit_in)}) :** Le client a déjà payé la majorité du camion. "
                    "Le solde restant est faible. **Les options 18 mois et 24 mois sont automatiquement refusées.** "
                    "Financer un petit reliquat sur 18-24 mois n'a aucun sens économique et bloquerait du capital pour des mensualités dérisoires. "
                    "**Durées proposées : 6 mois ou 12 mois.**"
                    if lang == "fr"
                    else f"💡 **High Deposit ({format_fcfa(client_deposit_in)}):** 18-month and 24-month terms are strictly excluded. "
                    "Financing a small remaining balance over 2 years needlessly ties up capital. **Offered terms: 6 or 12 months.**"
                )
            elif client_deposit_in >= 22_000_000.0:
                st.info(
                    f"💡 **Apport Moyen-Haut ({format_fcfa(client_deposit_in)}) :** Le solde est modéré. "
                    "Les durées conseillées sont **6, 12 ou 18 mois**. L'option 24 mois est retirée."
                    if lang == "fr"
                    else f"💡 **Medium-High Deposit ({format_fcfa(client_deposit_in)}):** Advised terms are 6, 12, or 18 months. 24 months is excluded."
                )
            else:
                st.info(
                    f"💡 **Apport Standard ({format_fcfa(client_deposit_in)}) :** "
                    "Le client finance une part substantielle du camion. "
                    "**Objectif de rentabilité validé :** pour 10M d'acompte sur 24 mois, le prix total est de **65 000 000 FCFA** "
                    "(soit **25 000 000 FCFA de bénéfice net** pour l'entreprise par rapport au coût de revient de 40M)."
                    if lang == "fr"
                    else f"💡 **Standard Deposit ({format_fcfa(client_deposit_in)}):** "
                    "Validated profit benchmark: for 10M deposit over 24 months, total contract price is **65,000,000 FCFA** "
                    "(**25,000,000 FCFA net company profit** on a 40M unit landed cost)."
                )

            st.caption(
                f"📊 **Paramètres clés :** Prix comptant : **{format_fcfa(market_sale_price)}** | "
                f"Coût de revient : **{format_fcfa(truck_landed_cost)}** | "
                f"Taux bancaire emprunt : **{annual_rate_pct:.1f}%/an** | "
                f"Taux commercial crédit-bail : **{commercial_lease_rate_pct:.2f}%/an**"
            )

    # Reference local market price
    base_cash_price_ref = market_sale_price

    # Educational banner explaining dynamic pricing logic
    st.info(
        f"💡 **Règle Fondamentale de Tarification Dynamique & Décomposition Financière :**\n"
        f"• **Valeur Comptant Normale du Camion :** **{format_fcfa(base_cash_price_ref)}**.\n"
        f"• **Capital Camion Financé :** Valeur Comptant ({format_fcfa(base_cash_price_ref)}) − Acompte Versé ({format_fcfa(client_deposit_in)}) = **{format_fcfa(max(0.0, base_cash_price_ref - client_deposit_in))}**.\n"
        f"• **Intérêts Crédit-Bail :** Calculés sur le capital immobilisé à **{commercial_lease_rate_pct:.2f}% / an**.\n"
        f"• **Dynamique Client :** Moins le client donne d'acompte (10M vs 30M), plus il retient du capital et plus il paie d'intérêts financiers.\n"
        f"• **Dynamique Durée :** Plus la durée s'allonge (6 à 24 mois), plus les intérêts cumulés rémunèrent l'immobilisation des fonds.\n"
        f"• **Cible Validée :** Pour 10M d'acompte sur 24 mois $\\rightarrow$ Intérêts = 19M FCFA $\\rightarrow$ **Prix Total = 65 000 000 FCFA** (Bénéfice Net Entreprise = **25 000 000 FCFA**)."
        if lang == "fr"
        else f"💡 **Dynamic Pricing Rule & Financial Breakdown:**\n"
        f"• **Normal Cash Asset Value:** **{format_fcfa(base_cash_price_ref)}**.\n"
        f"• **Financed Principal:** Cash Value ({format_fcfa(base_cash_price_ref)}) − Upfront Deposit ({format_fcfa(client_deposit_in)}) = **{format_fcfa(max(0.0, base_cash_price_ref - client_deposit_in))}**.\n"
        f"• **Leasing Interest:** Calculated on tied-up principal at **{commercial_lease_rate_pct:.2f}% / yr**.\n"
        f"• **Client Dynamics:** Lower deposit incurs more interest. Longer duration yields more interest.\n"
        f"• **Validated Target:** 10M deposit over 24 months $\\rightarrow$ +19M interest $\\rightarrow$ **Total = 65,000,000 FCFA** (**25,000,000 FCFA Net Profit**)."
    )

    # Generate Client Lease Options
    lease_options = generate_client_lease_options(
        truck_cost=truck_landed_cost,
        initial_deposit=client_deposit_in,
        base_cash_price=base_cash_price_ref,
        upfront_protection_costs=0.0,
        monthly_costs=0.0,
        target_annual_return=commercial_lease_rate_pct / 100.0,
        commercial_markup=sale_markup_pct / 100.0,
        discount_rate=financing_assumptions.annual_financing_rate,
    )

    st.markdown("---")
    st.markdown("### 📋 Options de Financement Proposées pour ce Client" if lang == "fr" else "### 📋 Financing Options for this Client")

    # Render 4 Cards for 6, 12, 18, 24 months
    cols_terms = st.columns(4)

    for idx, opt in enumerate(lease_options):
        with cols_terms[idx]:
            with st.container(border=True):
                st.markdown(f"### {opt.term_months} Mois" if lang == "fr" else f"### {opt.term_months} Months")

                if opt.is_recommended:
                    st.badge("🌟 Recommandé" if lang == "fr" else "🌟 Recommended", color="green")
                elif opt.is_offered:
                    st.badge("✅ Proposé" if lang == "fr" else "✅ Available", color="blue")
                else:
                    st.badge("🚫 Non Proposé" if lang == "fr" else "🚫 Not Offered", color="red")

                st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)

                if opt.is_offered:
                    st.metric(
                        "Traite Mensuelle" if lang == "fr" else "Monthly Payment",
                        format_fcfa(opt.monthly_installment),
                        f"pendant {opt.term_months} mois" if lang == "fr" else f"for {opt.term_months} months",
                    )
                    st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
                    st.write(f"• **Acompte le 1er jour :** {format_fcfa(opt.initial_deposit)}")
                    st.write(f"• **Capital camion financé :** {format_fcfa(opt.financed_balance)}")
                    st.write(f"• **Intérêts crédit-bail :** **+{format_fcfa(opt.total_interest_paid)}**")
                    st.write(f"• **Total mensualités :** {format_fcfa(opt.total_installments)}")
                    st.write(f"• **Prix total contrat :** **{format_fcfa(opt.total_contract_price)}**")
                    st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
                    st.write(f"💰 **Bénéfice Net Entreprise :** **{format_fcfa(opt.company_net_profit)}**")
                    st.caption(f"Gain net par camion (achat à {format_fcfa(truck_landed_cost)})" if lang == "fr" else f"Net gain / truck (cost {format_fcfa(truck_landed_cost)})")
                    st.write(f"⏳ **Remboursement camion :** **{opt.payback_month} mois**" if lang == "fr" else f"⏳ **Payback:** **{opt.payback_month} mo**")
                else:
                    st.metric("Traite Mensuelle" if lang == "fr" else "Monthly Payment", "—")
                    st.error(opt.rejection_reason)

    # Detailed Schedule Table & Printable Proposal
    st.markdown("---")
    st.markdown("### 🖨️ Devis Commercial Prêt à Imprimer / Télécharger" if lang == "fr" else "### 🖨️ Commercial Proposal Ready to Print / Download")

    offered_terms = [opt.term_months for opt in lease_options if opt.is_offered]
    if not offered_terms:
        offered_terms = [6, 12]

    selected_print_term = st.selectbox(
        "Sélectionnez la durée pour éditer le devis commercial :" if lang == "fr" else "Select duration for commercial quote:",
        options=offered_terms,
        format_func=lambda m: f"Durée {m} Mois ({format_fcfa(next(o.monthly_installment for o in lease_options if o.term_months == m))}/mois)" if lang == "fr" else f"{m} Months Quote",
    )

    chosen_opt = next(o for o in lease_options if o.term_months == selected_print_term)

    with st.container(border=True):
        st.markdown(
            f"#### 📜 DEVIS COMMERCIAL D'OFFRE EN CRÉDIT-BAIL\n"
            f"**Véhicule :** Camion Benne Chantier 20m³ | **Prix Comptant de Référence :** {format_fcfa(chosen_opt.base_cash_price)}"
        )
        q_c1, q_c2, q_c3 = st.columns(3)
        with q_c1:
            st.write(f"• **Valeur comptant du camion :** {format_fcfa(chosen_opt.base_cash_price)}")
            st.write(f"• **Apport initial (Acompte) :** {format_fcfa(chosen_opt.initial_deposit)}")
            st.write(f"• **Capital camion financé :** {format_fcfa(chosen_opt.financed_balance)}")
        with q_c2:
            st.write(f"• **Durée du crédit-bail :** {chosen_opt.term_months} mois")
            st.write(f"• **Intérêts crédit-bail :** +{format_fcfa(chosen_opt.total_interest_paid)}")
            st.write(f"• **Total des mensualités :** {format_fcfa(chosen_opt.total_installments)}")
        with q_c3:
            st.write(f"• **Traite mensuelle :** **{format_fcfa(chosen_opt.monthly_installment)} / mois**")
            st.write(f"• **Montant total du contrat :** **{format_fcfa(chosen_opt.total_contract_price)}**")
            st.write(f"• **Bénéfice Net Entreprise :** **{format_fcfa(chosen_opt.company_net_profit)}**")

        st.caption(
            "Conditions de validation : Sous réserve d'acceptation du dossier technique, versement de l'apport initial à la signature "
            "et souscription obligatoire de l'assurance tous risques avec balise GPS active."
            if lang == "fr"
            else "Validation terms: Subject to technical file approval, initial deposit at signing, and mandatory all-risk insurance with active GPS tracking."
        )

        if chosen_opt.evaluation:
            df_opt_sched = pd.DataFrame([
                {
                    "Mois": row.month,
                    "Solde Restant Dû": format_fcfa(row.opening_receivable),
                    "Traite Mensuelle": format_fcfa(row.installment),
                    "Nouveau Solde": format_fcfa(row.closing_receivable),
                    "Cumul Encaissé": format_fcfa(row.cumulative_cash_received),
                }
                for row in chosen_opt.evaluation.rows
            ])
            with st.expander("Consulter l'échéancier mensuel détaillé pour ce devis", expanded=False):
                st.dataframe(df_opt_sched, width="stretch", hide_index=True)


# ===========================================================================
# TAB 3: FLEET OPERATIONS & EXPLOITATION
# ===========================================================================
with tab_exploit:
    st.subheader(
        "🚜 Exploitation Directe de la Flotte de Bennes"
        if lang == "fr"
        else "🚜 Direct Fleet Exploitation"
    )
    st.markdown(
        "Exploitation directe des camions sur les chantiers générant des flux nets d'exploitation après carburant, chauffeurs et maintenance."
        if lang == "fr"
        else "Direct fleet operations producing net operational cash flows after operating charges and maintenance."
    )

    fleet_trucks_exploited = truck_count_input

    # Run exploitation evaluation for fleet size
    exploit_res = evaluate_exploitation(
        truck_cost=procurement_assumptions.effective_unit_cost,
        net_monthly_profit_per_truck=exploit_monthly_profit,
        downtime_rate=downtime_pct / 100.0,
        truck_count=fleet_trucks_exploited,
        horizon_months=loan_term_months,
    )
    df_exploit = exploitation_schedule_to_dataframe(exploit_res)

    ex_c1, ex_c2, ex_c3, ex_c4 = st.columns(4)
    with ex_c1:
        st.metric(
            "Gain Net / Benne / Mois (Réel)" if lang == "fr" else "Net Cash / Truck / Mo",
            format_fcfa(exploit_res.effective_monthly_cash_per_truck),
            f"-{downtime_pct:.0f}% d'indisponibilité déduits",
            help="Bénéfice net effectif après prise en compte des pannes et intempéries.",
            border=True,
        )
    with ex_c2:
        st.metric(
            f"Cash Mensuel Flotte ({fleet_trucks_exploited} Bennes)" if lang == "fr" else f"Fleet Monthly Cash ({fleet_trucks_exploited} Trucks)",
            format_fcfa(exploit_res.monthly_cash_fleet),
            f"Soit {format_fcfa(exploit_res.monthly_cash_fleet * 12)} / an",
            help="Rentrée de trésorerie nette mensuelle générée par l'ensemble de la flotte.",
            border=True,
        )
    with ex_c3:
        payback_display = f"{exploit_res.payback_period_months:.1f} mois" if exploit_res.payback_period_months else f"> {loan_term_months} mois"
        st.metric(
            "Temps de Rentabilisation (Payback)" if lang == "fr" else "Payback Period",
            payback_display,
            help="Nombre de mois nécessaires pour que les recettes d'exploitation couvrent intégralement l'achat des bennes.",
            border=True,
        )
    with ex_c4:
        st.metric(
            f"Cash Net Généré ({loan_term_months} mois)" if lang == "fr" else f"Net Cash Generated ({loan_term_months} mo)",
            format_fcfa(exploit_res.net_cash_generated),
            f"Total brut : {format_fcfa(exploit_res.total_cash_generated)}",
            help="Trésorerie nette finale après déduction du coût d'achat initial des camions.",
            border=True,
        )

    # Exploitation Trajectory Chart
    if not df_exploit.empty:
        fig_exp = go.Figure()
        fig_exp.add_trace(
            go.Scatter(
                x=df_exploit["Month"],
                y=df_exploit["Cumulative Generated"],
                mode="lines+markers",
                name="Gains Cumulés d'Exploitation" if lang == "fr" else "Cumulative Cash Generated",
                line=dict(color="#16A34A", width=3),
            )
        )
        fig_exp.add_trace(
            go.Bar(
                x=df_exploit["Month"],
                y=df_exploit["Net Monthly Cash"],
                name="Entrée Nette Mensuelle" if lang == "fr" else "Monthly Net Cash",
                marker_color="#2563EB",
                opacity=0.6,
            )
        )
        fig_exp.update_layout(xaxis_title="Mois" if lang == "fr" else "Month", yaxis_title="FCFA")
        apply_chart_style(fig_exp, title=f"Projection des Rentrées d'Exploitation ({fleet_trucks_exploited} Bennes)", height=340)
        st.plotly_chart(fig_exp, width="stretch")

        with st.expander("Consulter le tableau mois par mois de l'exploitation" if lang == "fr" else "View Month-by-Month Exploitation Table", expanded=False):
            df_exp_disp = df_exploit.copy()
            for col in ["Gross Operational", "Downtime Loss", "Net Monthly Cash", "Cumulative Generated", "Unrecovered Capital"]:
                if col in df_exp_disp.columns:
                    df_exp_disp[col] = df_exp_disp[col].apply(format_fcfa)
            st.dataframe(df_exp_disp, height=280, width="stretch", hide_index=True)


# ===========================================================================
# TAB 4: DIRECT CASH SALE
# ===========================================================================
with tab_sale:
    st.subheader(
        "💰 Vente Comptant Directe : Tarification & Marge"
        if lang == "fr"
        else "💰 Direct Cash Sale: Pricing & Margins"
    )
    st.markdown(
        f"Vente immédiate de camions au comptant. Évalue le prix plancher, la marge commerciale brute et le coût de portage financier de la dette."
        if lang == "fr"
        else "Direct cash sales per truck. Evaluates price floor, carrying cost, and transaction margins."
    )

    # Evaluate Cash Sale Pricing
    sale_pricing = evaluate_cash_sale_pricing(
        landed_cost=procurement_assumptions.effective_unit_cost,
        target_markup=sale_markup_pct / 100.0,
        holding_period_months=1,
        annual_financing_rate=financing_assumptions.annual_financing_rate,
    )
    sale_economics = evaluate_sale_price_economics(
        sale_price=market_sale_price,
        pricing=sale_pricing,
    )

    s_c1, s_c2, s_c3, s_c4 = st.columns(4)
    with s_c1:
        st.metric(
            "Prix de Vente Comptant (Marché)" if lang == "fr" else "Market Cash Price",
            format_fcfa(market_sale_price),
            f"Coût achat : {format_fcfa(truck_landed_cost)}",
            help="Prix de vente d'un camion sur le marché local.",
            border=True,
        )
    with s_c2:
        st.metric(
            "Marge Brute Réalisée" if lang == "fr" else "Gross Profit Realized",
            format_fcfa(sale_economics.gross_profit),
            f"{sale_economics.gross_margin:.1%} de marge brute",
            help="Différence entre le prix de vente et le coût de revient du camion.",
            border=True,
        )
    with s_c3:
        st.metric(
            "Portage Financier (1 mois à 15%)" if lang == "fr" else "Financing Carry Cost",
            format_fcfa(sale_pricing.financing_carry),
            help="Intérêts bancaires courus sur le camion pendant sa détention avant vente.",
            border=True,
        )
    with s_c4:
        st.metric(
            "Bénéfice Net après Portage" if lang == "fr" else "Net Profit After Carry",
            format_fcfa(sale_economics.net_profit),
            f"{sale_economics.net_margin:.1%} de marge nette",
            help="Gain net final restant dans l'entreprise après déduction des frais financiers de portage.",
            border=True,
        )

    st.markdown("---")
    st.markdown("##### 📊 Barème Comparatif des Prix de Vente Possibles" if lang == "fr" else "##### 📊 Market Price Comparison Table")

    df_market_comp = generate_market_comparison_table(
        pricing=sale_pricing,
        benchmark_prices=[42_000_000.0, 44_000_000.0, 46_000_000.0, 48_000_000.0, 50_000_000.0],
    )
    df_market_disp = df_market_comp.copy()
    for col in ["Offer Price", "Gross Profit", "Net Profit", "Margin vs Floor"]:
        if col in df_market_disp.columns:
            df_market_disp[col] = df_market_disp[col].apply(format_fcfa)
    for col in ["Gross Margin", "Net Margin", "Holding Period Return", "Annualized Return"]:
        if col in df_market_disp.columns:
            df_market_disp[col] = df_market_disp[col].apply(lambda x: f"{x:.1%}")

    st.dataframe(df_market_disp, width="stretch", hide_index=True)


# ===========================================================================
# TAB 5: SCENARIO MATRIX & SENSITIVITY
# ===========================================================================
with tab_scenarios:
    st.subheader(
        "🎯 Matrice des Scénarios & Analyse de Sensibilité"
        if lang == "fr"
        else "🎯 Scenario Matrix & Multi-Variable Sensitivity"
    )
    st.markdown(
        "Évaluez la robustesse de votre modèle financier face aux variations conjointes des paramètres : "
        "**Coût d'Achat** (38M, 40M, 42M FCFA) $\\times$ **Taux Bancaire** (15%, 20%, 25%) $\\times$ **Durée de Leasing** (6, 12, 18, 24 mois)."
        if lang == "fr"
        else "Evaluate financial robustness across 36 scenarios: "
        "Landed Cost (38M, 40M, 42M) × Financing Rate (15%, 20%, 25%) × Lease Term (6, 12, 18, 24 months)."
    )

    # 1. Preset Landed Cost Quick Comparison (38M, 40M, 42M)
    st.markdown("#### 1. Impact du Coût d'Achat par Benne (à taux fixe de 15% / an)" if lang == "fr" else "#### 1. Landed Cost Preset Comparison")

    df_preset_comp = run_preset_comparison(
        rate=annual_rate_pct / 100.0,
        term=24,
        loan_amount=loan_amount,
        loan_term_months=loan_term_months,
        lease_deposit=12_000_000.0,
        exploit_monthly_profit=exploit_monthly_profit,
        downtime=downtime_pct / 100.0,
    )

    sc_c1, sc_c2, sc_c3 = st.columns(3)
    preset_meta = [
        (sc_c1, "Scénario Favorable (38M FCFA)" if lang == "fr" else "Best Case (38M FCFA)", 0),
        (sc_c2, "Scénario Moyen (40M FCFA)" if lang == "fr" else "Average Case (40M FCFA)", 1),
        (sc_c3, "Scénario Tendu (42M FCFA)" if lang == "fr" else "Worst Case (42M FCFA)", 2),
    ]

    for col, title, idx in preset_meta:
        if idx < len(df_preset_comp):
            p_row = df_preset_comp.iloc[idx]
            with col:
                with st.container(border=True):
                    st.markdown(f"##### {title}")
                    st.metric("Prix Vente Recommandé" if lang == "fr" else "Rec. Sale Price", format_fcfa(p_row["Sale Rec Price"]))
                    st.metric("Prix Leasing Recommandé" if lang == "fr" else "Rec. Lease Price", format_fcfa(p_row["Lease Rec Price"]))
                    st.metric("Traite Mensuelle (24m)" if lang == "fr" else "Monthly Installment", format_fcfa(p_row["Lease Monthly Installment"]))

    st.markdown("---")
    st.markdown("#### 2. Matrice Complète des 36 Scénarios" if lang == "fr" else "#### 2. Full 36-Scenario Sensitivity Matrix")

    # Run full matrix
    with st.spinner("Calcul de la matrice de sensibilité..."):
        df_full_matrix = run_scenario_matrix(
            loan_amount=loan_amount,
            loan_term_months=loan_term_months,
            lease_deposit=12_000_000.0,
            exploit_monthly_profit=exploit_monthly_profit,
            exploit_downtime=downtime_pct / 100.0,
            required_reserve=min_cash_reserve,
        )

    # Interactive Filters
    f_c1, f_c2, f_c3 = st.columns(3)
    with f_c1:
        cost_filter = st.multiselect(
            "Filtrer Coût d'Achat" if lang == "fr" else "Filter Truck Cost",
            options=list(df_full_matrix["Scenario Cost"].unique()),
            default=list(df_full_matrix["Scenario Cost"].unique()),
        )
    with f_c2:
        rate_filter = st.multiselect(
            "Filtrer Taux Bancaire" if lang == "fr" else "Filter Interest Rate",
            options=[0.15, 0.20, 0.25],
            default=[0.15, 0.20, 0.25],
            format_func=lambda r: f"{r:.0%}",
        )
    with f_c3:
        term_filter = st.multiselect(
            "Filtrer Durée de Leasing" if lang == "fr" else "Filter Lease Term",
            options=[6, 12, 18, 24],
            default=[6, 12, 18, 24],
            format_func=lambda t: f"{t} mois" if lang == "fr" else f"{t} months",
        )

    filtered_matrix = df_full_matrix[
        (df_full_matrix["Scenario Cost"].isin(cost_filter))
        & (df_full_matrix["Financing Rate"].isin(rate_filter))
        & (df_full_matrix["Lease Term (Mos)"].isin(term_filter))
    ]

    # Format display columns
    df_matrix_display = filtered_matrix.copy()
    for col in ["Loan Principal", "Monthly Debt Service", "Total Debt Service", "Sale Rec Price", "Lease Rec Price", "Lease Monthly Installment", "Best Risk-Adjusted NPV"]:
        if col in df_matrix_display.columns:
            df_matrix_display[col] = df_matrix_display[col].apply(format_fcfa)
    if "Financing Rate" in df_matrix_display.columns:
        df_matrix_display["Financing Rate"] = df_matrix_display["Financing Rate"].apply(lambda r: f"{r:.0%}")

    st.dataframe(df_matrix_display, height=360, width="stretch", hide_index=True)

    st.download_button(
        "📥 Télécharger la Matrice de Sensibilité Complète (CSV)" if lang == "fr" else "📥 Download Full Matrix (CSV)",
        data=filtered_matrix.to_csv(index=False).encode("utf-8"),
        file_name="matrice_sensibilite_36_scenarios.csv",
        mime="text/csv",
    )
