"""Internationalization (i18n) module for French and English UI localization."""
from typing import Dict, Any, Optional

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # -------------------------------------------------------------------------
    # App Header & Metadata
    # -------------------------------------------------------------------------
    "app_title": {
        "en": "Dump Truck Finance & Leasing Simulator",
        "fr": "Simulateur Financier de Flotte de Bennes & Crédit-Bail",
    },
    "app_subtitle": {
        "en": "Deterministic Monthly Portfolio Allocation & Strategy Decision Engine (V1)",
        "fr": "Moteur d'arbitrage stratégique et simulation mensuelle déterministe de portefeuille (V1)",
    },
    "currency_badge": {
        "en": "Currency: FCFA (XAF)",
        "fr": "Devise : FCFA (XAF)",
    },
    "language_label": {
        "en": "Language",
        "fr": "Langue",
    },

    # -------------------------------------------------------------------------
    # Sidebar: Financing
    # -------------------------------------------------------------------------
    "sidebar_financing_title": {
        "en": "Global Financing",
        "fr": "Financement Bancaire Global",
    },
    "loan_amount": {
        "en": "Bank Loan Amount (FCFA)",
        "fr": "Montant du Prêt Bancaire (FCFA)",
    },
    "loan_amount_help": {
        "en": "Principal borrowed from bank to finance truck acquisitions.",
        "fr": "Capital emprunté auprès de la banque pour financer l'acquisition des bennes.",
    },
    "annual_rate": {
        "en": "Annual Financing Rate (%)",
        "fr": "Taux d'Intérêt Annuel (%)",
    },
    "annual_rate_help": {
        "en": "Nominal bank borrowing interest rate per annum.",
        "fr": "Taux d'intérêt nominal annuel appliqué par l'établissement financier.",
    },
    "loan_term": {
        "en": "Loan Term (Months)",
        "fr": "Durée du Prêt (Mois)",
    },
    "loan_term_help": {
        "en": "Bank debt amortization horizon in months.",
        "fr": "Horizon d'amortissement de la dette bancaire en mois.",
    },
    "expander_fees": {
        "en": "Bank Fees & Liquidity Reserves",
        "fr": "Frais de Dossier & Réserve de Sécurité",
    },
    "bank_fees": {
        "en": "Bank Arrangement Fees (FCFA)",
        "fr": "Frais d'Arrangement / Dossier Bancaire (FCFA)",
    },
    "other_charges": {
        "en": "Other Bank & Insurance Charges (FCFA)",
        "fr": "Autres Frais Bancaires & Assurances Prêt (FCFA)",
    },
    "starting_cash": {
        "en": "Starting Company Cash (FCFA)",
        "fr": "Trésorerie Initiale Disponible (FCFA)",
    },
    "min_cash_reserve": {
        "en": "Minimum Cash Reserve Buffer (FCFA)",
        "fr": "Réserve Minimale de Sécurité de Trésorerie (FCFA)",
    },
    "min_cash_reserve_help": {
        "en": "Untouchable liquidity threshold preserved before ordering any new batch of trucks.",
        "fr": "Seuil de liquidité intangible préservé avant tout nouvel achat de lot de bennes.",
    },

    # -------------------------------------------------------------------------
    # Sidebar: Procurement
    # -------------------------------------------------------------------------
    "sidebar_procurement_title": {
        "en": "Truck Cost & Procurement",
        "fr": "Acquisition & Coût des Bennes",
    },
    "truck_cost": {
        "en": "Landed Truck Cost (FCFA / truck)",
        "fr": "Coût Débarqué / Rendu Port (FCFA / benne)",
    },
    "preset_best": {
        "en": "Best Case (38M)",
        "fr": "Optimiste (38M)",
    },
    "preset_avg": {
        "en": "Average Case (40M)",
        "fr": "Moyen (40M)",
    },
    "preset_worst": {
        "en": "Worst Case (42M)",
        "fr": "Pessimiste (42M)",
    },
    "batch_size": {
        "en": "Procurement Batch Size (Multiples of 5)",
        "fr": "Taille de Lot d'Achat (Multiples de 5)",
    },
    "contingency_rate": {
        "en": "Procurement Contingency (%)",
        "fr": "Marge Imprévue / Douane (%)",
    },
    "contingency_amount": {
        "en": "Contingency Fixed Amount (FCFA)",
        "fr": "Montant Forfaitaire Imprévus (FCFA)",
    },

    # -------------------------------------------------------------------------
    # Sidebar: Tax & Regulatory
    # -------------------------------------------------------------------------
    "expander_taxes": {
        "en": "Taxes & Statutory Regime (Cameroon 2026 GTC)",
        "fr": "Fiscalité & Régime Statutaire (CGI 2026 Cameroun)",
    },
    "vat_statutory_label": {
        "en": "VAT Rate (%) [VERIFIED STATUTORY: Art. 149 CGI]",
        "fr": "Taux TVA (%) [STATUTAIRE VÉRIFIÉ : Art. 149 CGI]",
    },
    "vat_statutory_help": {
        "en": "17.5% base + 10% CAC = 19.25% verified rate under Cameroon General Tax Code.",
        "fr": "17,5% de base + 10% CAC = 19,25% statutaire vérifié selon le Code Général des Impôts.",
    },
    "vat_recoverable": {
        "en": "VAT is Recoverable [INPUT ASSUMPTION]",
        "fr": "TVA Déductible / Récupérable [HYPOTHÈSE UTILISATEUR]",
    },
    "cit_rate": {
        "en": "Corporate Income Tax (%) [INPUT ASSUMPTION]",
        "fr": "Impôt sur les Sociétés (IS %) [HYPOTHÈSE UTILISATEUR]",
    },
    "reg_fee": {
        "en": "Registration & Vehicle Title (FCFA) [INPUT ASSUMPTION]",
        "fr": "Frais d'Immatriculation & Carte Grise (FCFA) [HYPOTHÈSE]",
    },
    "road_tax": {
        "en": "Annual Road / Axle Tax (FCFA) [INPUT ASSUMPTION]",
        "fr": "Taxe à l'Essieu / Droit de Circulation Annuel (FCFA) [HYPOTHÈSE]",
    },

    # -------------------------------------------------------------------------
    # Main Tabs
    # -------------------------------------------------------------------------
    "tab_decision": {
        "en": "Executive Summary & Decision",
        "fr": "Synthèse Exécutive & Décision",
    },
    "tab_assumptions": {
        "en": "Financing & Fleet Procurement",
        "fr": "Financement & Achats de Bennes",
    },
    "tab_sale": {
        "en": "Strategy A: Cash Sale",
        "fr": "Stratégie A : Vente au Comptant",
    },
    "tab_leasing": {
        "en": "Strategy B: Client Leasing",
        "fr": "Stratégie B : Crédit-Bail / Leasing",
    },
    "tab_exploit": {
        "en": "Strategy C: Fleet Exploitation",
        "fr": "Stratégie C : Exploitation Flotte",
    },
    "tab_simulation": {
        "en": "Multi-Year Portfolio Simulation",
        "fr": "Simulation Mensuelle Multi-Annuelle",
    },
    "tab_scenarios": {
        "en": "Sensitivity Matrix (36 Scenarios)",
        "fr": "Matrice de Sensibilité (36 Scénarios)",
    },

    "client_proposal_title": {
        "en": "Client Leasing Proposal Generator",
        "fr": "Générateur d'Offres de Crédit-Bail Client",
    },
    "client_deposit_prompt": {
        "en": "Client Initial Down Payment / Deposit (FCFA)",
        "fr": "Apport Initial du Client (Acompte en FCFA)",
    },
    "client_proposal_desc": {
        "en": "Enter the client's available cash deposit to automatically generate all feasible financing terms (6, 12, 18, 24 months, max 2 years).",
        "fr": "Saisissez l'acompte que le client peut apporter pour générer automatiquement toutes les durées possibles (6, 12, 18 ou 24 mois, max 2 ans).",
    },
    "print_proposal_btn": {
        "en": "📄 Export Printable Client Proposal (PDF/Text)",
        "fr": "📄 Télécharger la Fiche de Proposition Client (Imprimable)",
    },
    "print_report_btn": {
        "en": "🖨️ Export Printable Business Simulation Summary",
        "fr": "🖨️ Télécharger le Rapport d'Activité Complet (Imprimable)",
    },
    # -------------------------------------------------------------------------
    # Top KPI Hero Banner
    # -------------------------------------------------------------------------
    "hero_total_financed": {
        "en": "Total Bank Debt Financed",
        "fr": "Total Emprunt Bancaire",
    },
    "hero_initial_fleet": {
        "en": "Initial Fleet Purchased",
        "fr": "Flotte Initiale Achetée",
    },
    "hero_capital_deployed": {
        "en": "Capital Deployed",
        "fr": "Capital Déployé",
    },
    "hero_remaining_liquidity": {
        "en": "Net Available Liquidity",
        "fr": "Trésorerie Nette Disponible",
    },
    "trucks_unit": {
        "en": "trucks",
        "fr": "bennes",
    },
    "batches_unit": {
        "en": "batches of 5",
        "fr": "lots de 5",
    },

    # -------------------------------------------------------------------------
    # Strategy Decision Engine (Section 12.1)
    # -------------------------------------------------------------------------
    "decision_title": {
        "en": "Strategic Investment Recommendation (Section 12.1)",
        "fr": "Recommandation d'Arbitrage Stratégique (Section 12.1)",
    },
    "decision_rule_desc": {
        "en": "Decision rule: Optimal Strategy = argmax(Risk-Adjusted NPV), subject to: (1) Cash Reserve Preserved, (2) Lease Deposit >= 10M FCFA, (3) Procurement in discrete multiples of 5.",
        "fr": "Règle de décision : Stratégie Optimale = argmax(VAN Corrigée du Risque), sous contraintes : (1) Réserve de liquidité préservée, (2) Dépôt de crédit-bail >= 10M FCFA, (3) Achats stricts par lots de 5 bennes.",
    },
    "recommended_badge": {
        "en": "RECOMMENDED STRATEGY",
        "fr": "STRATÉGIE RECOMMANDÉE",
    },
    "constraint_checks_title": {
        "en": "Statutory & Operational Invariants",
        "fr": "Vérification des Invariants Stratégiques",
    },
    "check_deposit": {
        "en": "Lease Deposit >= 10M FCFA",
        "fr": "Dépôt Client >= 10M FCFA",
    },
    "check_reserve": {
        "en": "Liquidity Reserve Protected",
        "fr": "Réserve de Liquidité Protégée",
    },
    "check_batches": {
        "en": "Discrete Batches (Multiples of 5)",
        "fr": "Commandes par Multiples de 5",
    },
    "comparative_cards_title": {
        "en": "Three Strategic Options at a Glance (Per Truck)",
        "fr": "Comparatif des Trois Options Stratégiques (Par Benne)",
    },
    "strategy_a_title": {
        "en": "Strategy A: Immediate Cash Sale",
        "fr": "Stratégie A : Vente au Comptant",
    },
    "strategy_b_title": {
        "en": "Strategy B: Client Leasing",
        "fr": "Stratégie B : Crédit-Bail Client",
    },
    "strategy_c_title": {
        "en": "Strategy C: Fleet Exploitation",
        "fr": "Stratégie C : Exploitation en Régie",
    },
    "risk_adj_npv": {
        "en": "Risk-Adjusted NPV",
        "fr": "VAN Corrigée du Risque",
    },
    "nominal_npv": {
        "en": "Nominal NPV",
        "fr": "VAN Nominale",
    },
    "net_profit": {
        "en": "Net Profit",
        "fr": "Bénéfice Net",
    },
    "gross_margin": {
        "en": "Gross Margin",
        "fr": "Marge Brute",
    },
    "roi": {
        "en": "Return on Investment (ROI)",
        "fr": "Retour sur Investissement (ROI)",
    },
    "annualized_irr": {
        "en": "Annualized IRR",
        "fr": "Taux de Rendement Interne (TRI)",
    },
    "payback_months": {
        "en": "Capital Payback Horizon",
        "fr": "Délai de Récupération (Payback)",
    },
    "immediate_inflow": {
        "en": "Immediate Cash Inflow",
        "fr": "Rentrée de Trésorerie Immédiate",
    },
    "liquidity_profile": {
        "en": "Liquidity Profile",
        "fr": "Profil de Liquidité",
    },
    "pros_title": {
        "en": "Strategic Advantages",
        "fr": "Avantages Stratégiques",
    },
    "cons_title": {
        "en": "Key Operational Risks",
        "fr": "Risques & Points de Vigilance",
    },

    # -------------------------------------------------------------------------
    # Warning Center
    # -------------------------------------------------------------------------
    "warning_center_title": {
        "en": "Real-Time Risk & Prudential Health Center",
        "fr": "Centre d'Alerte Prudentielle & Risques en Temps Réel",
    },
    "clean_status": {
        "en": "All prudential constraints, liquidity buffers, debt service ratios, and pricing floors are strictly satisfied.",
        "fr": "Tous les voyants sont au vert : réserves de liquidité, ratios de couverture de dette, et planchers de prix sont scrupuleusement respectés.",
    },

    # -------------------------------------------------------------------------
    # Strategy A: Cash Sale Panel
    # -------------------------------------------------------------------------
    "sale_header": {
        "en": "Strategy A: Direct Cash Sale Pricing & Turnaround",
        "fr": "Stratégie A : Tarification de Vente au Comptant & Rotation",
    },
    "target_markup": {
        "en": "Target Commercial Markup (%)",
        "fr": "Marge Commerciale Cible (%)",
    },
    "holding_period": {
        "en": "Inventory Holding Period (Months)",
        "fr": "Délai de Stockage / Rotation (Mois)",
    },
    "buyer_offer": {
        "en": "Evaluated Buyer Offer (FCFA)",
        "fr": "Offre de l'Acheteur Évaluée (FCFA)",
    },
    "price_floor": {
        "en": "Price Floor (Break-Even Minimum)",
        "fr": "Prix Plancher Strict (Seuil de Rentabilité)",
    },
    "recommended_price": {
        "en": "Recommended Selling Price",
        "fr": "Prix de Vente Conseillé",
    },
    "financing_carry": {
        "en": "Financing Carry Cost",
        "fr": "Coût de Portage Financier",
    },
    "viable_offer_msg": {
        "en": "Viable Offer: Price exceeds the floor with comfortable margin.",
        "fr": "Offre Rentable : Le prix proposé est supérieur au prix plancher avec une marge confortable.",
    },
    "sub_floor_offer_msg": {
        "en": "Sub-Floor Alert: Offer is below break-even cost floor! Margin erosion will occur.",
        "fr": "Alerte Prix Plancher : L'offre est inférieure au coût de revient plancher ! Risque de perte.",
    },

    # -------------------------------------------------------------------------
    # Strategy B: Customer Leasing Panel
    # -------------------------------------------------------------------------
    "lease_header": {
        "en": "Strategy B: Customer Leasing & Installment Plans",
        "fr": "Stratégie B : Crédit-Bail Client & Échéanciers",
    },
    "lease_term_label": {
        "en": "Contract Term (Months)",
        "fr": "Durée du Contrat (Mois)",
    },
    "initial_deposit_label": {
        "en": "Initial Customer Deposit (FCFA, min 10M)",
        "fr": "Dépôt Initial Client (FCFA, min 10M)",
    },
    "total_contract_price": {
        "en": "Total Contract Selling Price (FCFA)",
        "fr": "Prix Global du Contrat de Leasing (FCFA)",
    },
    "monthly_installment": {
        "en": "Customer Monthly Payment (FCFA/mo)",
        "fr": "Mensualité Facturée au Client (FCFA/mois)",
    },
    "security_costs_expander": {
        "en": "Section 9.1 Itemized Security & Risk Reserves",
        "fr": "Section 9.1 Frais de Sécurisation & Réserves de Risque",
    },
    "protection_cost_total": {
        "en": "Total Protection Cost per Leased Truck",
        "fr": "Coût Total de Protection par Benne Louée",
    },

    # -------------------------------------------------------------------------
    # Strategy C: Fleet Exploitation Panel
    # -------------------------------------------------------------------------
    "exploit_header": {
        "en": "Strategy C: Direct Fleet Operational Exploitation",
        "fr": "Stratégie C : Exploitation Directe de la Flotte en Régie",
    },
    "net_monthly_profit": {
        "en": "Net Operating Cash Flow per Truck (FCFA/mo)",
        "fr": "Cash-Flow Net d'Exploitation par Benne (FCFA/mois)",
    },
    "downtime_label": {
        "en": "Mechanical / Weather Downtime Allowance (%)",
        "fr": "Taux d'Immobilisation / Intempéries / Pannes (%)",
    },
    "effective_cash_truck": {
        "en": "Effective Monthly Cash Flow / Truck",
        "fr": "Cash Net Effectif par Benne / Mois",
    },
    "total_fleet_monthly": {
        "en": "Combined Fleet Monthly Operating Flow",
        "fr": "Cash-Flow Mensuel Total de la Flotte",
    },
    "payback_on_cost": {
        "en": "Payback Period on Acquisition Cost",
        "fr": "Délai d'Amortissement du Camion",
    },

    # -------------------------------------------------------------------------
    # Multi-Year Portfolio Simulation Panel
    # -------------------------------------------------------------------------
    "sim_header": {
        "en": "Multi-Year Portfolio Simulation & Reinvestment Dynamics",
        "fr": "Simulation de Portefeuille & Réinvestissement Dynamique",
    },
    "primary_strategy_label": {
        "en": "Active Portfolio Strategy",
        "fr": "Stratégie Active pour la Flotte",
    },
    "reinvest_toggle_label": {
        "en": "Enable Discrete Batch Reinvestment (Order 5 trucks when cash permits)",
        "fr": "Activer le Réinvestissement Automatique par Lots de 5 Bennes",
    },
    "closing_cash": {
        "en": "Final Cash Balance",
        "fr": "Trésorerie Finale de Clôture",
    },
    "final_debt": {
        "en": "Outstanding Debt Balance",
        "fr": "Dette Bancaire Restante",
    },
    "total_trucks_acquired": {
        "en": "Total Trucks Procured",
        "fr": "Nombre Total de Bennes Achetées",
    },
    "reinvestment_batches": {
        "en": "Reinvestment Batches Ordered",
        "fr": "Lots Supplémentaires Commandés",
    },
    "dscr_label": {
        "en": "Debt Service Coverage Ratio (DSCR)",
        "fr": "Ratio de Couverture du Service de la Dette (DSCR)",
    },
    "min_cash_experienced": {
        "en": "Minimum Cash Experienced",
        "fr": "Trésorerie la Plus Basse Atteinte",
    },

    # -------------------------------------------------------------------------
    # Scenario Matrix (36 Scenarios)
    # -------------------------------------------------------------------------
    "scenario_matrix_header": {
        "en": "Sensitivity Matrix Across 36 Operational Scenarios",
        "fr": "Matrice de Sensibilité sur 36 Scénarios Opérationnels",
    },
    "preset_comparison_header": {
        "en": "Landed Cost Presets Sensitivity (Best 38M, Avg 40M, Worst 42M)",
        "fr": "Sensibilité aux Hypothèses de Coût Débarqué (38M, 40M, 42M FCFA)",
    },
    "full_matrix_header": {
        "en": "Full 36-Scenario Parameter Grid",
        "fr": "Grille Complète des 36 Combinaisons Stratégiques",
    },
    "dominant_strategy": {
        "en": "Dominant Recommended Strategy",
        "fr": "Stratégie Dominante Recommandée",
    },
    "average_best_npv": {
        "en": "Average Risk-Adjusted NPV",
        "fr": "VAN Moyenne Corrigée du Risque",
    },
    "download_csv": {
        "en": "Download Dataset (CSV)",
        "fr": "Télécharger les Données (CSV)",
    },

    # -------------------------------------------------------------------------
    # Business Analyst & Navigation Pages
    # -------------------------------------------------------------------------
    "nav_page_analyst": {
        "en": "💼 Strategic Simulator & Business Analyst",
        "fr": "💼 Simulateur Stratégique & Analyste Business",
    },
    "nav_page_client_leasing": {
        "en": "🤝 Customer Leasing Offer Generator",
        "fr": "🤝 Espace Offres & Devis Client Leasing",
    },
    "nav_page_comparison": {
        "en": "⚖️ Strategy Benchmark & Stress-Testing",
        "fr": "⚖️ Comparateur de Plans & Stress-Test",
    },
    "sim_horizon_years": {
        "en": "Simulation Horizon (Years)",
        "fr": "Horizon de Simulation Souhaité (Années)",
    },
    "sim_horizon_years_help": {
        "en": "Enter the number of years you want to simulate (1 to 5 years).",
        "fr": "Nombre d'années sur lesquelles vous souhaitez projeter les flux et la rentabilité du business (1 à 5 ans).",
    },
    "bank_loan_years": {
        "en": "Bank Loan Duration (Years)",
        "fr": "Durée du Prêt Bancaire (Années)",
    },
    "exploit_net_profit_per_truck": {
        "en": "Estimated Operating Net Profit / Truck / Month (FCFA)",
        "fr": "Bénéfice Net d'Exploitation Estimé / Camion / Mois (FCFA)",
    },
    "exploit_net_profit_help": {
        "en": "Estimated monthly net operating profit per active truck in company exploitation (after fuel, driver, operational fees).",
        "fr": "Revenu net estimé généré par 1 benne en exploitation mensuelle (après déduction carburant, chauffeur, péages).",
    },
    "portfolio_strategy_mode": {
        "en": "Fleet Strategy Mode",
        "fr": "Mode de Déploiement de la Flotte",
    },
    "mode_optimizer": {
        "en": "🤖 Business Analyst Optimizer (Find Best Combination)",
        "fr": "🤖 Optimiseur Analyste Business (Trouver le Meilleur Plan Combiné)",
    },
    "mode_custom": {
        "en": "🎛️ Custom Strategy Allocation Mix",
        "fr": "🎛️ Répartition Personnalisée Sur-Mesure",
    },
    "reinvest_toggle_label": {
        "en": "Automatically Reinvest Cash Surplus in New 5-Truck Batches",
        "fr": "Réinvestir Automatiquement les Excédents en Nouveaux Lots de 5 Bennes",
    },
    "analyst_diagnosis_title": {
        "en": "📋 Business Analyst Audit & Recommendations",
        "fr": "📋 Audit & Recommandations de l'Analyste Business",
    },
    "optimal_plan_banner": {
        "en": "🏆 Optimal Recommended Fleet Plan",
        "fr": "🏆 Plan de Déploiement Recommandé par l'Analyste",
    },
    "ranked_plans_title": {
        "en": "📊 Comparison Ranking Across Fleet Strategies",
        "fr": "📊 Classement Comparatif des Stratégies de Flotte",
    },
    "total_net_cash_profit": {
        "en": "Total Net Cash Profit (FCFA)",
        "fr": "Bénéfice Net Total en FCFA",
    },
    "final_cash_in_bank": {
        "en": "Cash Balance in Bank at End (FCFA)",
        "fr": "Trésorerie Finale en Banque (FCFA)",
    },
    "loan_repayment_status": {
        "en": "Bank Loan Paid Off At",
        "fr": "Dette Bancaire Apurée au",
    },
    "reserve_safety_status": {
        "en": "Safety Reserve Preserved",
        "fr": "Réserve de Sécurité Préservée",
    },
}


def t(key: str, lang: str = "fr", **kwargs: Any) -> str:
    """Retrieve localized string for given key and language (defaults to French)."""
    lang_key = "fr" if str(lang).lower().startswith("fr") else "en"
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key.replace("_", " ").title()
    text = entry.get(lang_key, entry.get("fr", key))
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text

