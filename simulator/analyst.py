"""Business Analyst & Portfolio Optimization Engine.
Evaluates pure and combined hybrid strategies to determine the most profitable
and financially solvent fleet deployment plan over a user-defined simulation horizon.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd

from simulator.primitives import (
    annual_to_monthly_rate,
    format_fcfa,
    format_pct,
    validate_positive_number,
    validate_rate,
)
from simulator.models import (
    FinancingAssumptions,
    ProcurementAssumptions,
    CashSaleAssumptions,
    LeaseAssumptions,
    ExploitationAssumptions,
    ProtectionCostConfig,
    TaxConfig,
)
from simulator.portfolio import StrategyType, TruckState
from simulator.simulation import (
    SimulationConfig,
    SimulationResult,
    run_portfolio_simulation,
    simulation_to_dataframe,
)


@dataclass
class PortfolioPlan:
    """Evaluated portfolio deployment plan with financial outcomes and risk analysis."""
    name: str
    allocation: Dict[StrategyType, float]
    description: str
    result: SimulationResult
    total_net_profit: float
    final_cash: float
    debt_payoff_month: Optional[int]
    min_cash_balance: float
    is_cash_reserve_preserved: bool
    total_trucks_operated: int
    dscr_average: float
    risk_level: str
    score: float
    pros: List[str]
    cons: List[str]


def evaluate_single_plan(
    name: str,
    allocation: Dict[StrategyType, float],
    description: str,
    financing: FinancingAssumptions,
    procurement: ProcurementAssumptions,
    cash_sale: CashSaleAssumptions,
    lease: LeaseAssumptions,
    exploitation: ExploitationAssumptions,
    protection_config: ProtectionCostConfig,
    tax_config: TaxConfig,
    horizon_months: int,
    reinvest_cash: bool = True,
) -> PortfolioPlan:
    """Run a discrete simulation for a specific strategy allocation and calculate analyst metrics."""
    # Determine primary strategy fallback (largest allocation)
    primary_strat = max(allocation.items(), key=lambda kv: kv[1])[0]

    config = SimulationConfig(
        financing=financing,
        procurement=procurement,
        primary_strategy=primary_strat,
        strategy_allocation=allocation,
        cash_sale=cash_sale,
        lease=lease,
        exploitation=exploitation,
        protection_config=protection_config,
        tax_config=tax_config,
        horizon_months=horizon_months,
        reinvest_cash=reinvest_cash,
    )

    result = run_portfolio_simulation(config)

    # Debt payoff month
    debt_payoff_month: Optional[int] = None
    for s in result.snapshots:
        if s.closing_debt <= 1.0:
            debt_payoff_month = s.month
            break

    # Calculate average DSCR during loan repayment period
    dscr_values: List[float] = []
    for s in result.snapshots:
        if s.outflows_debt_service > 0:
            noi = s.inflows_exploitation + s.inflows_lease_installments - s.outflows_operating - s.outflows_protection
            dscr_values.append(max(0.0, noi / s.outflows_debt_service))
    avg_dscr = (sum(dscr_values) / len(dscr_values)) if dscr_values else 2.0

    # Net Profit over the horizon:
    # Final cash + value of active assets + remaining receivables - initial starting equity - remaining debt
    # In pure cash terms: (cumulative cash inflows - cumulative operating/protection outflows - debt service)
    total_net_cash_profit = (
        result.cumulative_cash_generated
        - sum(s.outflows_operating + s.outflows_protection for s in result.snapshots)
        - result.cumulative_debt_service_paid
    )

    reserve_ok = result.minimum_cash_experienced >= financing.min_cash_reserve

    # Risk level classification
    exp_pct = allocation.get(StrategyType.EXPLOITATION, 0.0)
    lease_pct = allocation.get(StrategyType.LEASING, 0.0)
    sale_pct = allocation.get(StrategyType.CASH_SALE, 0.0)

    if exp_pct >= 0.70:
        risk_level = "Élevé (Sensibilité forte aux pannes et gestion opérationnelle)"
    elif exp_pct >= 0.40 or lease_pct >= 0.60:
        risk_level = "Modéré (Équilibre exploitation et créances sécurisées)"
    else:
        risk_level = "Faible (Revenus rapides et risques opérationnels réduits)"

    # Solvency & Profitability Scoring
    # Heavy penalty if reserve is breached or if debt cannot be paid
    solvency_mult = 1.0 if reserve_ok else 0.4
    dscr_mult = min(1.5, max(0.5, avg_dscr / 1.2)) if avg_dscr > 0 else 0.5
    raw_score = max(0.0, total_net_cash_profit) * solvency_mult * dscr_mult
    score = raw_score / 1_000_000.0  # Normalized score

    # Pros and cons
    pros: List[str]
    cons: List[str]
    if exp_pct >= 0.5 and lease_pct >= 0.2 and sale_pct >= 0.1:
        pros = [
            "Diversification optimale des sources de revenus",
            "Acomptes de leasing et ventes apportent des liquidités immédiates",
            "Exploitation directe assure un fort cash-flow mensuel pérenne",
        ]
        cons = [
            "Nécessite la gestion simultanée de 3 activités (commerciale, crédit, exploitation)",
        ]
    elif exp_pct >= 0.8:
        pros = [
            "Rendement mensuel brut maximal sur le long terme",
            "Plein contrôle sur les camions et les contrats de transport",
        ]
        cons = [
            "Risque opérationnel maximal (pannes, saison des pluies, carburant)",
            "Aucun acompte immédiat perçu au démarrage",
        ]
    elif lease_pct >= 0.8:
        pros = [
            "Acomptes immédiats sécurisés dès la signature",
            "Zéro risque d'entretien mécanique (à la charge du client)",
            "Mensualités prévisibles et garanties par contrat",
        ]
        cons = [
            "Risque de retard ou défaut de paiement du client",
            "Marge totale plafonnée par le contrat de leasing",
        ]
    elif sale_pct >= 0.8:
        pros = [
            "Libération de trésorerie ultra-rapide",
            "Zéro risque opérationnel ou de recouvrement",
        ]
        cons = [
            "Bénéfice unique sans flux récurrent",
            "Nécessite de racheter immédiatement de nouveaux camions",
        ]
    else:
        pros = [
            "Bon compromis entre liquidité immédiate et revenus réguliers",
            "Capacité à honorer les échéances bancaires",
        ]
        cons = [
            "Exige une gestion administrative rigoureuse",
        ]

    return PortfolioPlan(
        name=name,
        allocation=allocation,
        description=description,
        result=result,
        total_net_profit=total_net_cash_profit,
        final_cash=result.final_cash,
        debt_payoff_month=debt_payoff_month,
        min_cash_balance=result.minimum_cash_experienced,
        is_cash_reserve_preserved=reserve_ok,
        total_trucks_operated=result.total_trucks_purchased,
        dscr_average=avg_dscr,
        risk_level=risk_level,
        score=score,
        pros=pros,
        cons=cons,
    )


def run_business_analyst_optimizer(
    financing: FinancingAssumptions,
    procurement: ProcurementAssumptions,
    cash_sale: CashSaleAssumptions,
    lease: LeaseAssumptions,
    exploitation: ExploitationAssumptions,
    protection_config: ProtectionCostConfig,
    tax_config: TaxConfig,
    horizon_years: int = 3,
    custom_allocation: Optional[Dict[StrategyType, float]] = None,
    reinvest_cash: bool = True,
) -> Dict[str, Any]:
    """Run full Business Analyst simulation across candidate portfolio plans.
    
    Returns:
        {
            "recommended_plan": PortfolioPlan,
            "all_plans": List[PortfolioPlan],
            "custom_plan": Optional[PortfolioPlan],
            "insights": Dict[str, Any],
        }
    """
    validate_positive_number("Simulation years", horizon_years, allow_zero=False)
    horizon_months = int(horizon_years * 12)

    # Standard candidate plans to evaluate and compare
    candidate_definitions = [
        (
            "Mix Équilibré Optimal (50% Exploitation / 30% Leasing / 20% Vente)",
            {StrategyType.EXPLOITATION: 0.50, StrategyType.LEASING: 0.30, StrategyType.CASH_SALE: 0.20},
            "Stratégie combinée : fortes rentrées mensuelles d'exploitation, sécurité des créances de leasing et liquidité immédiate des ventes comptant.",
        ),
        (
            "Mix Revenu Récurrent (60% Exploitation / 40% Leasing)",
            {StrategyType.EXPLOITATION: 0.60, StrategyType.LEASING: 0.40, StrategyType.CASH_SALE: 0.0},
            "Accent sur les flux continus : exploitation directe renforcée et portefeuille de leasing à moyen terme.",
        ),
        (
            "Mix Trésorerie Rapide (30% Exploitation / 40% Leasing / 30% Vente)",
            {StrategyType.EXPLOITATION: 0.30, StrategyType.LEASING: 0.40, StrategyType.CASH_SALE: 0.30},
            "Accent sur la liquidité et la réduction du risque mécanique tout en maintenant le service de la dette bancaire.",
        ),
        (
            "100% Exploitation Interne (Pure Flotte)",
            {StrategyType.EXPLOITATION: 1.0, StrategyType.LEASING: 0.0, StrategyType.CASH_SALE: 0.0},
            "Tous les camions sont exploités par l'entreprise : rentabilité brute théorique maximale mais risque opérationnel total.",
        ),
        (
            "100% Leasing Clients (Pure Crédit-Bail)",
            {StrategyType.EXPLOITATION: 0.0, StrategyType.LEASING: 1.0, StrategyType.CASH_SALE: 0.0},
            "Tous les camions sont confiés en leasing avec acompte initial : entretien à la charge du client, mensualités fixes.",
        ),
        (
            "100% Vente Comptant (Pure Négoce)",
            {StrategyType.EXPLOITATION: 0.0, StrategyType.LEASING: 0.0, StrategyType.CASH_SALE: 1.0},
            "Rotation immédiate : revente dès l'arrivée pour dégager du cash sans engagement d'exploitation.",
        ),
    ]

    all_plans: List[PortfolioPlan] = []
    for name, alloc, desc in candidate_definitions:
        plan = evaluate_single_plan(
            name=name,
            allocation=alloc,
            description=desc,
            financing=financing,
            procurement=procurement,
            cash_sale=cash_sale,
            lease=lease,
            exploitation=exploitation,
            protection_config=protection_config,
            tax_config=tax_config,
            horizon_months=horizon_months,
            reinvest_cash=reinvest_cash,
        )
        all_plans.append(plan)

    # Sort plans by score descending
    all_plans.sort(key=lambda p: p.score, reverse=True)
    recommended_plan = all_plans[0]

    # Evaluate custom plan if requested
    custom_plan: Optional[PortfolioPlan] = None
    if custom_allocation:
        custom_plan = evaluate_single_plan(
            name="Plan Personnalisé Utilisateur",
            allocation=custom_allocation,
            description="Répartition sur-mesure choisie par l'utilisateur.",
            financing=financing,
            procurement=procurement,
            cash_sale=cash_sale,
            lease=lease,
            exploitation=exploitation,
            protection_config=protection_config,
            tax_config=tax_config,
            horizon_months=horizon_months,
            reinvest_cash=reinvest_cash,
        )

    # Generate Analyst Insights
    insights = generate_analyst_insights(
        recommended_plan=recommended_plan,
        financing=financing,
        horizon_years=horizon_years,
    )

    return {
        "recommended_plan": recommended_plan,
        "all_plans": all_plans,
        "custom_plan": custom_plan,
        "insights": insights,
        "horizon_years": horizon_years,
        "horizon_months": horizon_months,
    }


def generate_analyst_insights(
    recommended_plan: PortfolioPlan,
    financing: FinancingAssumptions,
    horizon_years: int,
) -> Dict[str, str]:
    """Generate professional, clear, real-world business commentary and advice."""
    r_plan = recommended_plan
    res = r_plan.result

    # 1. Trésorerie et capacité de remboursement
    monthly_debt = res.snapshots[0].outflows_debt_service if res.snapshots else 0.0
    debt_text = (
        f"L'emprunt bancaire de {format_fcfa(financing.bank_loan_amount)} impose une mensualité de {format_fcfa(monthly_debt)} "
        f"sur {int(financing.loan_term_months / 12)} ans. Avec le plan '{r_plan.name}', la trésorerie mensuelle moyenne couvre cette charge "
        f"avec un ratio de couverture (DSCR) moyen de {r_plan.dscr_average:.2f}x."
    )

    # 2. Clôture de dette et trésorerie finale
    payoff_text = (
        f"À l'horizon de simulation de {horizon_years} an(s) ({horizon_years * 12} mois), "
        f"la dette bancaire est clôturée dès le mois {r_plan.debt_payoff_month or 'N/A'}. "
        f"La trésorerie nette en banque atteint {format_fcfa(r_plan.final_cash)} "
        f"et le bénéfice net de trésorerie cumulé s'élève à {format_fcfa(r_plan.total_net_profit)}."
    )

    # 3. Réalité terrain vs Simulation
    real_world_warning = (
        "💡 Vigilance Réalité Terrain : Les modèles mathématiques supposent un encaissement fluide. "
        "Dans la réalité en Afrique Centrale (aléas climatiques de saison des pluies, retards de paiement de chantiers, pannes d'injecteurs), "
        "il est impératif de sanctuariser la réserve de sécurité de "
        f"{format_fcfa(financing.min_cash_reserve)} en banque pour ne jamais vous retrouver en défaut de paiement bancaire."
    )

    # 4. Pourquoi combiner les stratégies ?
    why_combine = (
        "⚖️ Pourquoi la combinaison est supérieure à une stratégie unique ?\n"
        "- L'Exploitation seule génère beaucoup de cash brut, mais vous expose à 100% des coûts d'ateliers et de carburant.\n"
        "- Le Leasing seul transfère la maintenance au client et rapporte un acompte immédiat, mais plafonne votre gain.\n"
        "- La Vente comptant dégage du cash instantané sans aucun risque, mais ne crée pas de flux régulier.\n"
        "👉 Combiner permet aux acomptes de leasing et aux ventes de payer immédiatement les premières traites de banque, "
        "tandis que l'exploitation assure la richesse sur la durée."
    )

    return {
        "debt_diagnosis": debt_text,
        "payoff_and_cash": payoff_text,
        "real_world_warning": real_world_warning,
        "why_combine": why_combine,
    }

