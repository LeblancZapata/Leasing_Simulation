"""Dump Truck Finance & Leasing Simulator - Business Analyst & Strategic Decision Cockpit.
Provides multi-page navigation:
1. Business Analyst & Portfolio Optimizer (Multi-strategy simulation across user-defined horizon)
2. Customer Leasing Offer Generator (Deposit-driven 6, 12, 18, 24 mo proposals & print quotes)
3. Strategy Benchmarking & Stress-Testing (Multi-plan ranking & sensitivity analysis)
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
    StrategyType,
    t,
    TRANSLATIONS,
    generate_client_lease_options,
    ClientLeaseOption,
    PortfolioPlan,
    evaluate_single_plan,
    run_business_analyst_optimizer,
    generate_analyst_insights,
    run_scenario_matrix,
    run_preset_comparison,
    SimulationConfig,
    run_portfolio_simulation,
    simulation_to_dataframe,
)
from simulator.sale import evaluate_cash_sale_pricing, evaluate_sale_price_economics
from simulator.exploitation import evaluate_exploitation

# ---------------------------------------------------------------------------
# Streamlit Application Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Simulateur Financier & Commercial : Bennes & Leasing",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Chart Styling Utility
# ---------------------------------------------------------------------------
def apply_chart_style(fig: go.Figure, title: str = "", height: int = 370) -> go.Figure:
    """Apply high-contrast, modern slate aesthetic to Plotly figures."""
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family="Inter, sans-serif", size=15, color="#0F172A", weight=600),
        ),
        font=dict(family="Inter, sans-serif", size=12, color="#475569"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,0.7)",
        height=height,
        margin=dict(l=20, r=20, t=45, b=25),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor="#E2E8F0",
            borderwidth=1,
        ),
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0", linecolor="#CBD5E1", tickfont=dict(size=11)),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0", linecolor="#CBD5E1", tickfont=dict(size=11)),
        hoverlabel=dict(bgcolor="#0F172A", font_size=12, font_family="Inter, sans-serif", font_color="#FFFFFF"),
    )
    return fig


# ---------------------------------------------------------------------------
# Sidebar: Navigation & Comprehensive Business Parameters
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🌐 Langue / Language")
    lang_choice = st.segmented_control(
        "Langue",
        options=["Français 🇫🇷", "English 🇬🇧"],
        default="Français 🇫🇷",
        label_visibility="collapsed",
    )
    lang = "fr" if "Français" in (lang_choice or "Français") else "en"

    st.markdown("---")
    st.markdown("### 🧭 Navigation")
    nav_page = st.radio(
        "Sélectionnez l'espace de travail :",
        options=[
            "💼 1. Simulateur Stratégique & Analyste" if lang == "fr" else "💼 1. Strategic Simulator & Analyst",
            "🤝 2. Espace Offre Client Leasing" if lang == "fr" else "🤝 2. Client Leasing Proposals",
            "⚖️ 3. Comparateur de Plans & Stress-Test" if lang == "fr" else "⚖️ 3. Benchmark & Stress-Testing",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### 🏦 1. Financement Bancaire & Horizon" if lang == "fr" else "### 🏦 1. Bank Financing & Horizon")

    loan_amount = st.number_input(
        "Montant Emprunté à la Banque (FCFA)" if lang == "fr" else "Bank Loan Amount (FCFA)",
        min_value=0.0,
        max_value=5_000_000_000.0,
        value=500_000_000.0,
        step=20_000_000.0,
        format="%.0f",
        help="Montant principal emprunté à la banque pour financer les bennes.",
    )

    annual_rate_pct = st.slider(
        "Taux d'Intérêt Annuel (%)" if lang == "fr" else "Annual Interest Rate (%)",
        min_value=0.0,
        max_value=30.0,
        value=12.0,
        step=0.5,
    )

    bank_loan_years = st.slider(
        "Durée du Prêt Bancaire (Années)" if lang == "fr" else "Bank Loan Duration (Years)",
        min_value=1,
        max_value=5,
        value=3,
        step=1,
        help="Nombre d'années pour rembourser le crédit bancaire (ex: 3 ans = 36 mois).",
    )
    loan_term_months = bank_loan_years * 12

    # User-defined Simulation Horizon in Years
    sim_horizon_years = st.slider(
        "Durée de la Simulation Souhaitée (Années)" if lang == "fr" else "Simulation Horizon (Years)",
        min_value=1,
        max_value=5,
        value=3,
        step=1,
        help="Nombre d'années sur lesquelles vous souhaitez projeter les flux et la rentabilité du business.",
    )
    horizon_months = sim_horizon_years * 12

    min_cash_reserve = st.number_input(
        "Réserve de Sécurité Minimale en Banque (FCFA)" if lang == "fr" else "Minimum Safety Reserve (FCFA)",
        min_value=0.0,
        value=50_000_000.0,
        step=5_000_000.0,
        format="%.0f",
        help="Trésorerie intouchable gardée en banque pour parer aux aléas.",
    )

    st.markdown("---")
    st.markdown("### 🚛 2. Achat des Bennes" if lang == "fr" else "### 🚛 2. Dump Truck Procurement")

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
    )

    batch_size = st.selectbox(
        "Taille de Lot Acheté (Multiples de 5)" if lang == "fr" else "Batch Size (Multiples of 5)",
        options=[5, 10, 15, 20],
        index=0,
        help="Les camions sont obligatoirement commandés par lots de 5 bennes.",
    )

    st.markdown("---")
    st.markdown("### ⚙️ 3. Paramètres d'Exploitation & Marché" if lang == "fr" else "### ⚙️ 3. Operations & Market Parameters")

    exploit_monthly_profit = st.number_input(
        "Bénéfice Net Estimé / Benne / Mois (FCFA)" if lang == "fr" else "Est. Net Profit / Truck / Month (FCFA)",
        min_value=500_000.0,
        max_value=10_000_000.0,
        value=3_000_000.0,
        step=250_000.0,
        format="%.0f",
        help="Gain net moyen d'un camion benne en exploitation (après carburant, chauffeur et frais de route).",
    )

    downtime_pct = st.slider(
        "Taux d'Indisponibilité / Pannes (%)" if lang == "fr" else "Downtime / Breakdown Rate (%)",
        min_value=0.0,
        max_value=30.0,
        value=10.0,
        step=1.0,
        help="Pourcentage moyen de temps perdu pour pannes, maintenance ou intempéries.",
    )

    with st.expander("🛠️ Paramètres Complémentaires (Vente & Réinvestissement)" if lang == "fr" else "🛠️ Additional Parameters", expanded=False):
        sale_markup_pct = st.slider("Marge Brute Vente Comptant (%)", min_value=5.0, max_value=40.0, value=20.0, step=1.0)
        reinvest_toggle = st.checkbox(
            "Réinvestir automatiquement les excédents de trésorerie en nouveaux lots de 5 camions"
            if lang == "fr"
            else "Automatically reinvest cash surplus in new 5-truck batches",
            value=True,
        )
        starting_cash_in = st.number_input("Trésorerie Initiale Propre (FCFA)", min_value=0.0, value=0.0, step=1_000_000.0, format="%.0f")


# ---------------------------------------------------------------------------
# Core Object Instantiations
# ---------------------------------------------------------------------------
financing_assumptions = FinancingAssumptions(
    bank_loan_amount=loan_amount,
    annual_financing_rate=annual_rate_pct / 100.0,
    loan_term_months=loan_term_months,
    starting_cash=starting_cash_in,
    min_cash_reserve=min_cash_reserve,
)

procurement_assumptions = ProcurementAssumptions(
    landed_cost=truck_landed_cost,
    batch_step=batch_size,
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
    target_annual_return=0.25,
)

protection_config = ProtectionCostConfig()
tax_config = TaxConfig()

# Loan schedule pre-calculation
loan_schedule = generate_loan_schedule_from_assumptions(financing_assumptions)
df_loan_sched = schedule_to_dataframe(loan_schedule)
monthly_bank_payment = loan_schedule.rows[0].payment if loan_schedule.rows else 0.0

# Initial batch purchase evaluation
net_procurement_cash = starting_cash_in + loan_amount
initial_procurement_eval = evaluate_procurement_from_assumptions(
    available_cash=net_procurement_cash,
    financing=financing_assumptions,
    procurement=procurement_assumptions,
)


# ===========================================================================
# TOP BANNER: EXECUTIVE KPI SUMMARY
# ===========================================================================
st.title("🚚 Cockpit Stratégique : Financement & Déploiement de Bennes" if lang == "fr" else "🚚 Strategic Fleet Financing & Leasing Cockpit")
st.caption(
    "Simulation déterministe d'aide à la décision : optimisation du portefeuille de flotte, génération de devis de crédit-bail et audit de trésorerie."
    if lang == "fr"
    else "Deterministic decision-support engine: fleet portfolio optimization, client leasing quote generator, and cash flow audit."
)

with st.container(horizontal=True):
    st.metric(
        "💰 Emprunt Bancaire" if lang == "fr" else "Bank Loan",
        format_fcfa(loan_amount),
        f"Traite : {format_fcfa(monthly_bank_payment)} / mois sur {bank_loan_years} ans",
        border=True,
    )
    st.metric(
        "🚛 Bennes Achetées au Départ" if lang == "fr" else "Initial Trucks Procured",
        f"{initial_procurement_eval.purchasable_trucks} bennes",
        f"Coût : {format_fcfa(initial_procurement_eval.total_batch_cost)}",
        border=True,
    )
    st.metric(
        "⏳ Horizon de Simulation" if lang == "fr" else "Simulation Horizon",
        f"{sim_horizon_years} an(s) ({horizon_months} mois)",
        f"Durée choisie par l'utilisateur",
        border=True,
    )
    st.metric(
        "🛡️ Réserve de Sécurité" if lang == "fr" else "Safety Cash Reserve",
        format_fcfa(min_cash_reserve),
        "Sanctuarisée en banque",
        border=True,
    )

st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)


# ===========================================================================
# PAGE 1: BUSINESS ANALYST & STRATEGIC PORTFOLIO OPTIMIZER
# ===========================================================================
if "1." in nav_page:
    st.subheader(
        "💼 Analyse Stratégique & Optimisation du Portefeuille de Flotte"
        if lang == "fr"
        else "💼 Strategic Portfolio Analysis & Fleet Optimization"
    )
    st.markdown(
        "Un chef d'entreprise ne se limite pas à une seule stratégie rigide. "
        "L'analyste business simule les **combinaisons optimales** (mélange d'exploitation directe, de leasing client et de vente comptant) "
        "pour identifier le plan qui maximise votre bénéfice net tout en sécurisant le remboursement de la dette bancaire sur vos **{} an(s)**."
        .format(sim_horizon_years)
        if lang == "fr"
        else "A business leader rarely relies on a single rigid strategy. "
        "The business analyst simulates **optimal combinations** (mixing direct fleet exploitation, client leasing, and cash sales) "
        "to discover the plan that maximizes net cash profit while securing bank debt repayment over your **{} year(s)**."
        .format(sim_horizon_years)
    )

    # Strategy Mode Selection
    mode_col1, mode_col2 = st.columns([1, 1])
    with mode_col1:
        strategy_mode = st.segmented_control(
            "Mode de Déploiement",
            options=[
                "🏆 Recherche Automatique du Plan Optimal (Recommandé)" if lang == "fr" else "🏆 Automatic Optimal Plan Finder (Recommended)",
                "🎛️ Répartition Personnalisée Sur-Mesure" if lang == "fr" else "🎛️ Custom Strategy Allocation Mix",
            ],
            default="🏆 Recherche Automatique du Plan Optimal (Recommandé)" if lang == "fr" else "🏆 Automatic Optimal Plan Finder (Recommended)",
        )

    # Custom Allocation Sliders if selected
    custom_allocation_dict: Optional[Dict[StrategyType, float]] = None
    if "Personnalisée" in (strategy_mode or "") or "Custom" in (strategy_mode or ""):
        with st.container(border=True):
            st.markdown("#### 🎛️ Définissez Votre Répartition de Flotte Souhaitée" if lang == "fr" else "#### 🎛️ Configure Your Fleet Allocation")
            st.caption("Ajustez les pourcentages pour répartir vos bennes entre les 3 activités (total normalisé à 100%) :")
            sm1, sm2, sm3 = st.columns(3)
            with sm1:
                p_exp = st.slider("% Exploitation Interne (Régie)", min_value=0, max_value=100, value=50, step=10)
            with sm2:
                p_lease = st.slider("% Crédit-Bail Client (Leasing)", min_value=0, max_value=100, value=30, step=10)
            with sm3:
                p_sale = st.slider("% Vente au Comptant", min_value=0, max_value=100, value=20, step=10)

            sum_p = p_exp + p_lease + p_sale
            if sum_p <= 0:
                p_exp, p_lease, p_sale = 50, 30, 20
                sum_p = 100
            custom_allocation_dict = {
                StrategyType.EXPLOITATION: p_exp / sum_p,
                StrategyType.LEASING: p_lease / sum_p,
                StrategyType.CASH_SALE: p_sale / sum_p,
            }
            st.info(
                f"Répartition effective calculée : **{custom_allocation_dict[StrategyType.EXPLOITATION]:.0%} Exploitation** | "
                f"**{custom_allocation_dict[StrategyType.LEASING]:.0%} Leasing** | "
                f"**{custom_allocation_dict[StrategyType.CASH_SALE]:.0%} Vente Comptant**"
            )

    # Run Business Analyst Optimizer
    with st.spinner("L'analyste business simule les trajectoires de flotte..." if lang == "fr" else "Business analyst running simulations..."):
        optimizer_output = run_business_analyst_optimizer(
            financing=financing_assumptions,
            procurement=procurement_assumptions,
            cash_sale=cash_sale_assumptions,
            lease=lease_assumptions,
            exploitation=exploitation_assumptions,
            protection_config=protection_config,
            tax_config=tax_config,
            horizon_years=sim_horizon_years,
            custom_allocation=custom_allocation_dict,
            reinvest_cash=reinvest_toggle,
        )

    # Active plan to display
    active_plan: PortfolioPlan = (
        optimizer_output["custom_plan"]
        if (custom_allocation_dict and optimizer_output["custom_plan"])
        else optimizer_output["recommended_plan"]
    )
    insights = optimizer_output["insights"]

    # Render Chosen / Recommended Plan Card
    st.markdown("---")
    with st.container(border=True):
        st.markdown(f"### 🏆 {active_plan.name}")
        st.write(active_plan.description)

        # Plan Allocation Badges
        alloc_exp_pct = active_plan.allocation.get(StrategyType.EXPLOITATION, 0.0)
        alloc_lease_pct = active_plan.allocation.get(StrategyType.LEASING, 0.0)
        alloc_sale_pct = active_plan.allocation.get(StrategyType.CASH_SALE, 0.0)

        # How many trucks initially go where
        init_trucks = initial_procurement_eval.purchasable_trucks
        init_exp_cnt = round(init_trucks * alloc_exp_pct)
        init_lease_cnt = round(init_trucks * alloc_lease_pct)
        init_sale_cnt = max(0, init_trucks - init_exp_cnt - init_lease_cnt)

        st.markdown(
            f"**Affectation du 1er lot ({init_trucks} bennes) :** "
            f"`{init_exp_cnt} bennes en Exploitation ({alloc_exp_pct:.0%})` · "
            f"`{init_lease_cnt} bennes en Leasing ({alloc_lease_pct:.0%})` · "
            f"`{init_sale_cnt} bennes en Vente Comptant ({alloc_sale_pct:.0%})`"
        )

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)

        # 4 Key Plain-Language Metrics (No NPV jargon!)
        pm1, pm2, pm3, pm4 = st.columns(4)
        with pm1:
            st.metric(
                "💰 Bénéfice Net Total en FCFA" if lang == "fr" else "Total Net Cash Profit",
                format_fcfa(active_plan.total_net_profit),
                f"Sur {sim_horizon_years} an(s) d'activité",
                border=True,
            )
        with pm2:
            st.metric(
                "🏦 Trésorerie Finale en Banque" if lang == "fr" else "Final Cash in Bank",
                format_fcfa(active_plan.final_cash),
                f"+{format_fcfa(max(0.0, active_plan.final_cash - min_cash_reserve))} au-dessus de la réserve",
                border=True,
            )
        with pm3:
            st.metric(
                "📅 Dette Bancaire Apurée au" if lang == "fr" else "Bank Loan Paid Off At",
                f"Mois {active_plan.debt_payoff_month or 'Terminé'}" if active_plan.debt_payoff_month else "En cours",
                f"Prêt de {bank_loan_years} ans",
                border=True,
            )
        with pm4:
            st.metric(
                "🛡️ Coussin de Trésorerie Minimal" if lang == "fr" else "Min Cash Cushion",
                format_fcfa(active_plan.min_cash_balance),
                "Réserve Préservée ✅" if active_plan.is_cash_reserve_preserved else "⚠️ Risque de tension",
                border=True,
            )

    # Visual Simulation Charts
    st.markdown("---")
    st.markdown("#### 📊 Trajectoire de Trésorerie & Couverture de Dette sur {} An(s)" if lang == "fr" else "#### 📊 Cash Trajectory & Debt Coverage over {} Year(s)".format(sim_horizon_years))

    df_sim_active = simulation_to_dataframe(active_plan.result)

    fig_plan_cash = go.Figure()
    fig_plan_cash.add_trace(
        go.Scatter(
            x=df_sim_active["Month"],
            y=df_sim_active["Closing Cash"],
            mode="lines",
            name="Solde de Trésorerie en Banque",
            fill="tozeroy",
            fillcolor="rgba(22, 163, 74, 0.12)",
            line=dict(color="#16A34A", width=3),
        )
    )
    fig_plan_cash.add_trace(
        go.Scatter(
            x=df_sim_active["Month"],
            y=df_sim_active["Closing Debt"],
            mode="lines",
            name="Dette Bancaire Restante",
            line=dict(color="#DC2626", width=2.5),
        )
    )
    fig_plan_cash.add_trace(
        go.Scatter(
            x=df_sim_active["Month"],
            y=[min_cash_reserve] * len(df_sim_active),
            mode="lines",
            name="Réserve de Sécurité Intouchable",
            line=dict(color="#D97706", width=2, dash="dash"),
        )
    )
    apply_chart_style(
        fig_plan_cash,
        title=f"Évolution de la Trésorerie vs Dette Bancaire (Mois 1 à {horizon_months})",
        height=360,
    )
    st.plotly_chart(fig_plan_cash, width="stretch")

    # Inflows Breakdown Chart
    fig_inflows = go.Figure()
    fig_inflows.add_trace(
        go.Bar(
            x=df_sim_active["Month"],
            y=df_sim_active["Exploitation Cash"],
            name="Cash Exploitation Flotte",
            marker_color="#2563EB",
        )
    )
    fig_inflows.add_trace(
        go.Bar(
            x=df_sim_active["Month"],
            y=df_sim_active["Lease Installments"] + df_sim_active["Lease Deposits"],
            name="Cash Leasing (Acomptes + Traites)",
            marker_color="#16A34A",
        )
    )
    fig_inflows.add_trace(
        go.Bar(
            x=df_sim_active["Month"],
            y=df_sim_active["Sales Proceeds"],
            name="Ventes Comptant",
            marker_color="#F59E0B",
        )
    )
    fig_inflows.update_layout(barmode="stack", yaxis_title="FCFA")
    apply_chart_style(fig_inflows, title=f"Composition Mensuelle des Entrées d'Argent (FCFA)", height=320)
    st.plotly_chart(fig_inflows, width="stretch")

    # Month-by-Month Trajectory Table Expander
    with st.expander(
        f"📋 Consulter le Tableau Mois par Mois de Votre Activité (Mois 1 à {horizon_months})"
        if lang == "fr"
        else f"📋 View Month-by-Month Activity Table (Month 1 to {horizon_months})",
        expanded=False,
    ):
        df_display_plan = pd.DataFrame({
            "Mois": df_sim_active["Month"],
            "Trésorerie Début": df_sim_active["Opening Cash"].apply(format_fcfa),
            "Entrées d'Argent": df_sim_active["Total Inflows"].apply(format_fcfa),
            "Traite Bancaire Payée": df_sim_active["Debt Service"].apply(format_fcfa),
            "Nouvelles Bennes Achetées": df_sim_active["Reinvestment Trucks"].apply(lambda n: f"+{n}" if n > 0 else "—"),
            "Trésorerie Fin de Mois": df_sim_active["Closing Cash"].apply(format_fcfa),
            "Dette Bancaire Restante": df_sim_active["Closing Debt"].apply(format_fcfa),
            "Taille Flotte": df_sim_active["Fleet Size"].apply(lambda n: f"{n} bennes"),
        })
        st.dataframe(df_display_plan, height=320, width="stretch", hide_index=True)

        st.download_button(
            "📥 Télécharger les Données Complètes de la Simulation (CSV)" if lang == "fr" else "📥 Download Simulation Data (CSV)",
            data=df_sim_active.to_csv(index=False).encode("utf-8"),
            file_name=f"simulation_analyste_{sim_horizon_years}ans.csv",
            mime="text/csv",
        )

    # Business Analyst Audit & Real-World Commentary
    st.markdown("---")
    st.markdown("### 📋 Audit & Recommandations de l'Analyste Business" if lang == "fr" else "### 📋 Business Analyst Audit & Advice")

    an_c1, an_c2 = st.columns(2)
    with an_c1:
        with st.container(border=True):
            st.markdown("##### 🏦 Diagnostic de Trésorerie & Dette" if lang == "fr" else "##### 🏦 Debt & Cash Flow Diagnosis")
            st.write(insights["debt_diagnosis"])
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            st.markdown("##### 📅 Horizon & Bénéfice Cumulé" if lang == "fr" else "##### 📅 Payoff & Final Profit")
            st.write(insights["payoff_and_cash"])

    with an_c2:
        with st.container(border=True):
            st.markdown("##### 💡 Vigilance Réalité Terrain" if lang == "fr" else "##### 💡 Real-World Field Caution")
            st.warning(insights["real_world_warning"])
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            st.markdown("##### ⚖️ Pourquoi Combiner les Stratégies ?" if lang == "fr" else "##### ⚖️ Why Combine Strategies?")
            st.info(insights["why_combine"])

    # Disclaimer Note
    st.caption(
        "⚠️ **Note méthodologique importante :** Ces simulations constituent un outil d'aide à la décision stratégique fondé sur des calculs déterministes. "
        "Les performances réelles dépendent des aléas du marché, de la rigueur de suivi de maintenance des bennes, des conditions météorologiques et de la ponctualité des tiers."
        if lang == "fr"
        else "⚠️ **Methodological Notice:** These simulations serve as a strategic decision-support model based on deterministic formulas. "
        "Actual outcomes depend on operational discipline, weather, client reliability, and vehicle maintenance."
    )


# ===========================================================================
# PAGE 2: CLIENT LEASING OFFER GENERATOR (DEDICATED TO CLIENT)
# ===========================================================================
elif "2." in nav_page:
    st.subheader(
        "🤝 Espace Offre & Devis Commercial pour Client Intéressé par le Leasing"
        if lang == "fr"
        else "🤝 Client Leasing Quote & Proposal Generator"
    )
    st.markdown(
        "Cet écran est spécialement conçu pour négocier avec un **client souhaitant acquérir une benne en crédit-bail**. "
        "Saisissez ce que le client propose comme apport initial (acompte). "
        "Le système calcule immédiatement les **durées réalistes possibles** (6, 12, 18 ou 24 mois, max 2 ans) adaptées à cet apport."
        if lang == "fr"
        else "This workspace is built specifically to structure offers for **clients interested in leasing dump trucks**. "
        "Enter the client's initial deposit. "
        "The system calculates realistic terms (6, 12, 18, 24 months, strictly ≤ 2 years) tailored to that down payment."
    )

    # Prompt the user for the client's deposit
    p_col1, p_col2 = st.columns([2, 3])
    with p_col1:
        with st.container(border=True):
            st.markdown("#### Apport Proposé par le Client" if lang == "fr" else "#### Client Down Payment")
            client_deposit_in = st.number_input(
                "Combien le client verse-t-il comme apport initial (FCFA) ?" if lang == "fr" else "Initial deposit provided by client (FCFA)?",
                min_value=10_000_000.0,
                max_value=80_000_000.0,
                value=12_000_000.0,
                step=1_000_000.0,
                format="%.0f",
                help="Statutairement, l'acompte ne peut pas être inférieur à 10 000 000 FCFA.",
            )

            st.markdown("**Raccourcis rapides :**" if lang == "fr" else "**Quick shortcuts:**")
            quick_chips = st.segmented_control(
                "Montants typiques",
                options=["10M FCFA", "12M FCFA", "15M FCFA", "20M FCFA", "25M FCFA", "30M FCFA"],
                default="12M FCFA" if client_deposit_in == 12_000_000.0 else None,
                label_visibility="collapsed",
            )
            if quick_chips:
                val_num = float(quick_chips.replace("M FCFA", "")) * 1_000_000.0
                if val_num != client_deposit_in:
                    client_deposit_in = val_num

    with p_col2:
        with st.container(border=True):
            st.markdown("#### Règle de Décision Commerciale" if lang == "fr" else "#### Commercial Decision Rule")
            if client_deposit_in >= 28_000_000.0:
                st.warning(
                    f"💡 **Apport Élevé ({format_fcfa(client_deposit_in)}) :** Le client a déjà payé la majorité du camion ({truck_landed_cost/1e6:.0f}M). "
                    "Le solde restant est très faible. **Les options 18 mois et 24 mois sont automatiquement refusées.** "
                    "Financer un petit solde sur 18-24 mois n'a aucun sens économique pour vous et bloquerait du capital pour des mensualités dérisoires. "
                    "**Durées proposées : 6 mois ou 12 mois.**"
                    if lang == "fr"
                    else f"💡 **High Deposit ({format_fcfa(client_deposit_in)}):** The client pays most of the truck upfront. "
                    "18-month and 24-month terms are strictly excluded. Extending a tiny balance over 2 years needlessly ties up capital. "
                    "**Offered terms: 6 or 12 months.**"
                )
            elif client_deposit_in >= 22_000_000.0:
                st.info(
                    f"💡 **Apport Moyen-Haut ({format_fcfa(client_deposit_in)}) :** Le solde est modéré. Les durées conseillées sont **6, 12 ou 18 mois**. L'option 24 mois est retirée."
                    if lang == "fr"
                    else f"💡 **Medium-High Deposit ({format_fcfa(client_deposit_in)}):** Advised terms are 6, 12, or 18 months. 24 months is excluded."
                )
            else:
                st.info(
                    f"💡 **Apport Standard ({format_fcfa(client_deposit_in)}) :** Le client apporte environ 25% à 35% du véhicule. "
                    "Pour que la mensualité reste supportable avec les revenus de ses chantiers, les durées recommandées sont **18 mois ou 24 mois**."
                    if lang == "fr"
                    else f"💡 **Standard Deposit ({format_fcfa(client_deposit_in)}):** Recommended terms are 18 or 24 months to keep monthly installments affordable."
                )

    # Generate Client Lease Options
    lease_options = generate_client_lease_options(
        truck_cost=truck_landed_cost,
        initial_deposit=client_deposit_in,
        upfront_protection_costs=2_000_000.0,
        monthly_costs=15_000.0,
        target_annual_return=0.25,
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
                        "Mensualité Client" if lang == "fr" else "Monthly Payment",
                        format_fcfa(opt.monthly_installment),
                        f"pendant {opt.term_months} mois",
                    )
                    st.write(f"• **Acompte le 1er jour :** {format_fcfa(opt.initial_deposit)}")
                    st.write(f"• **Reliquat financé :** {format_fcfa(opt.financed_balance)}")
                    st.write(f"• **Prix total client :** **{format_fcfa(opt.total_contract_price)}**")
                    st.markdown("---")
                    st.write(f"💰 **Bénéfice Net Entreprise :** **{format_fcfa(opt.company_net_profit)}**")
                    st.write(f"⏳ **Camion amorti en :** **{opt.payback_month} mois**")
                else:
                    st.metric("Mensualité" if lang == "fr" else "Monthly Payment", "—")
                    st.error(opt.rejection_reason)

    # Printable Commercial Proposal Generator
    st.markdown("---")
    st.markdown("### 🖨️ Devis Commercial Prêt à Imprimer / Télécharger" if lang == "fr" else "### 🖨️ Commercial Proposal Ready to Print / Download")

    offered_terms = [opt.term_months for opt in lease_options if opt.is_offered]
    if not offered_terms:
        offered_terms = [12, 24]

    selected_print_term = st.selectbox(
        "Sélectionnez la durée pour imprimer le devis commercial :" if lang == "fr" else "Select duration for commercial quote:",
        options=offered_terms,
        format_func=lambda m: f"Durée {m} Mois ({format_fcfa(next(o.monthly_installment for o in lease_options if o.term_months == m))}/mois)" if lang == "fr" else f"{m} Months Quote",
    )

    chosen_opt = next(o for o in lease_options if o.term_months == selected_print_term)

    with st.container(border=True):
        proposal_text = f"""========================================================================================
                  PROPOSITION COMMERCIALE DE CRÉDIT-BAIL / LOCATION-VENTE
========================================================================================

Objet : Financement et mise à disposition d'un Camion Benne 20m³
Date d'émission : 2026

1. CONDITIONS FINANCIÈRES :
   -------------------------------------------------------------------------------------
   • Désignation du véhicule        : Camion Benne 20m³ (Neuf / Rendu Port)
   • Valeur de base du véhicule     : {format_fcfa(truck_landed_cost)}
   • APPORT INITIAL CLIENT (ACOMPTE): {format_fcfa(chosen_opt.initial_deposit)} (Payable à la commande)
   • Solde restant financé          : {format_fcfa(chosen_opt.financed_balance)}
   • Durée du contrat               : {chosen_opt.term_months} MOIS (Strictement <= 2 ans)
   • MENSUALITÉ FIXE DU CLIENT      : {format_fcfa(chosen_opt.monthly_installment)} / MOIS
   • PRIX TOTAL FACTURÉ AU CLIENT   : {format_fcfa(chosen_opt.total_contract_price)}

2. CONDITIONS GÉNÉRALES & SÉCURITÉ :
   -------------------------------------------------------------------------------------
   • Balise GPS / Télématique avec coupure moteur installée et active 24/7.
   • Entretien courant, pneumatiques et chauffeurs à la charge exclusive du client.
   • Transfert de propriété du camion au client dès parfait paiement de la dernière traite.
   • Dépôt de garantie conservé par la société bailleresse jusqu'au terme du contrat.

3. BILAN FINANCIER POUR LA SOCIÉTÉ BAILLERESSE :
   -------------------------------------------------------------------------------------
   • Marge brute dégagée            : {format_fcfa(chosen_opt.company_net_profit)}
   • Horizon de remboursement       : {chosen_opt.payback_month} mois
========================================================================================"""
        st.code(proposal_text, language="text")

        st.download_button(
            "📄 Télécharger le Devis Commercial (TXT)" if lang == "fr" else "📄 Download Commercial Quote (TXT)",
            data=proposal_text,
            file_name=f"devis_commercial_leasing_{chosen_opt.term_months}mois.txt",
            mime="text/plain",
        )


# ===========================================================================
# PAGE 3: STRATEGY BENCHMARKING & STRESS-TESTING
# ===========================================================================
else:
    st.subheader(
        "⚖️ Comparateur de Plans Stratégiques & Stress-Test Opérationnel"
        if lang == "fr"
        else "⚖️ Strategy Benchmark & Operational Stress-Testing"
    )
    st.markdown(
        "Comparez toutes les options de déploiement de flotte côte-à-côte sur votre horizon de **{} an(s)**, "
        "et testez la résistance de votre entreprise face aux imprévus du monde réel."
        .format(sim_horizon_years)
        if lang == "fr"
        else "Compare all fleet strategies side-by-side across your **{} year(s)** horizon, "
        "and test how your business withstands real-world stress scenarios."
        .format(sim_horizon_years)
    )

    # Multi-plan ranking table
    with st.spinner("Comparaison de tous les plans..."):
        full_benchmark = run_business_analyst_optimizer(
            financing=financing_assumptions,
            procurement=procurement_assumptions,
            cash_sale=cash_sale_assumptions,
            lease=lease_assumptions,
            exploitation=exploitation_assumptions,
            protection_config=protection_config,
            tax_config=tax_config,
            horizon_years=sim_horizon_years,
            reinvest_cash=reinvest_toggle,
        )

    all_plans_list = full_benchmark["all_plans"]

    st.markdown("#### 📊 Classement Comparatif des Stratégies" if lang == "fr" else "#### 📊 Strategy Comparison Ranking")

    plan_rows = []
    for idx, p in enumerate(all_plans_list, 1):
        plan_rows.append({
            "Rang": f"#{idx}",
            "Nom du Plan": p.name,
            "Bénéfice Net Total (FCFA)": format_fcfa(p.total_net_profit),
            "Trésorerie Finale en Banque": format_fcfa(p.final_cash),
            "Fin de Dette": f"Mois {p.debt_payoff_month}" if p.debt_payoff_month else "En cours",
            "Couverture Dette (DSCR)": f"{p.dscr_average:.2f}x",
            "Niveau de Risque": p.risk_level.split(" (")[0],
            "Score Analyste": f"{p.score:.1f}",
        })
    df_ranking = pd.DataFrame(plan_rows)
    st.dataframe(df_ranking, width="stretch", hide_index=True)

    # Comparative Bar Chart
    fig_comp_plans = go.Figure()
    fig_comp_plans.add_trace(
        go.Bar(
            name="Bénéfice Net Total (FCFA)",
            x=[p.name.split(" (")[0] for p in all_plans_list],
            y=[p.total_net_profit for p in all_plans_list],
            marker_color="#16A34A",
            text=[format_fcfa(p.total_net_profit) for p in all_plans_list],
            textposition="outside",
        )
    )
    fig_comp_plans.add_trace(
        go.Bar(
            name="Trésorerie Finale en Banque",
            x=[p.name.split(" (")[0] for p in all_plans_list],
            y=[p.final_cash for p in all_plans_list],
            marker_color="#2563EB",
            text=[format_fcfa(p.final_cash) for p in all_plans_list],
            textposition="outside",
        )
    )
    fig_comp_plans.update_layout(barmode="group", yaxis_title="FCFA")
    apply_chart_style(fig_comp_plans, title=f"Comparatif Financier Direct sur {sim_horizon_years} An(s)", height=350)
    st.plotly_chart(fig_comp_plans, width="stretch")

    # Stress-Testing Section
    st.markdown("---")
    st.markdown("#### 🌪️ Simulateur de Stress-Test : Que se passe-t-il en cas de crise ?" if lang == "fr" else "#### 🌪️ Stress-Testing: What Happens During a Downside Shock?")

    st.markdown(
        "Dans la réalité, des aléas surviennent (saison des pluies prolongée, hausse soudaine du carburant, pannes en cascade). "
        "Simulez l'impact d'une dégradation de vos paramètres :"
        if lang == "fr"
        else "In real life, adverse shocks happen (extended rainy seasons, diesel price spikes, multiple breakdowns). "
        "Test resilience against operational shocks:"
    )

    st_c1, st_c2 = st.columns(2)
    with st_c1:
        exploit_shock_pct = st.slider(
            "Choc sur les Revenus d'Exploitation (%)" if lang == "fr" else "Exploitation Revenue Shock (%)",
            min_value=-50,
            max_value=0,
            value=-20,
            step=5,
            help="Baisse simulée des gains mensuels d'exploitation.",
        )
    with st_c2:
        rate_shock_pct = st.slider(
            "Hausse du Taux d'Intérêt Bancaire (+%)" if lang == "fr" else "Bank Interest Rate Hike (+%)",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.5,
            help="Augmentation imprévue du coût du crédit bancaire.",
        )

    # Stressed assumptions
    stressed_exploit = ExploitationAssumptions(
        net_monthly_profit_per_truck=max(500_000.0, exploit_monthly_profit * (1.0 + exploit_shock_pct / 100.0)),
        downtime_allowance_rate=min(0.40, downtime_pct / 100.0 + 0.05),
    )
    stressed_financing = FinancingAssumptions(
        bank_loan_amount=loan_amount,
        annual_financing_rate=(annual_rate_pct + rate_shock_pct) / 100.0,
        loan_term_months=loan_term_months,
        starting_cash=starting_cash_in,
        min_cash_reserve=min_cash_reserve,
    )

    stressed_benchmark = run_business_analyst_optimizer(
        financing=stressed_financing,
        procurement=procurement_assumptions,
        cash_sale=cash_sale_assumptions,
        lease=lease_assumptions,
        exploitation=stressed_exploit,
        protection_config=protection_config,
        tax_config=tax_config,
        horizon_years=sim_horizon_years,
        reinvest_cash=reinvest_toggle,
    )

    rec_base = full_benchmark["recommended_plan"]
    rec_stress = stressed_benchmark["recommended_plan"]

    sc_k1, sc_k2, sc_k3 = st.columns(3)
    with sc_k1:
        delta_profit = rec_stress.total_net_profit - rec_base.total_net_profit
        st.metric(
            "Bénéfice Net sous Stress" if lang == "fr" else "Stressed Net Profit",
            format_fcfa(rec_stress.total_net_profit),
            f"{format_fcfa(delta_profit)} d'écart",
            border=True,
        )
    with sc_k2:
        st.metric(
            "Trésorerie sous Stress" if lang == "fr" else "Stressed Cash Balance",
            format_fcfa(rec_stress.final_cash),
            f"Réserve {format_fcfa(min_cash_reserve)}",
            border=True,
        )
    with sc_k3:
        st.metric(
            "Statut de Solvabilité" if lang == "fr" else "Solvency Status",
            "Solvable & Résistant ✅" if rec_stress.is_cash_reserve_preserved else "⚠️ Tension de Trésorerie",
            f"DSCR : {rec_stress.dscr_average:.2f}x",
            border=True,
        )

    # 36-Scenario Matrix (Collapsible for accountants)
    with st.expander("🔬 Consulter la Matrice Complète des 36 Scénarios Sensibilité (Optionnel)" if lang == "fr" else "🔬 View Full 36-Scenario Grid (Optional)", expanded=False):
        df_matrix_full = run_scenario_matrix(
            loan_amount=loan_amount,
            loan_term_months=loan_term_months,
            lease_deposit=12_000_000.0,
            required_reserve=min_cash_reserve,
        )
        st.dataframe(df_matrix_full, width="stretch", hide_index=True)
