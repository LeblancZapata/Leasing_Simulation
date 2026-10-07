"""Discrete monthly portfolio simulation engine adhering to Section 11 specifications."""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import numpy_financial as npf

from simulator.primitives import (
    annual_to_monthly_rate,
    validate_positive_number,
    validate_rate,
    SimulatorValidationError,
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
from simulator.loan import generate_loan_schedule_from_assumptions
from simulator.acquisition import (
    calculate_purchasable_trucks,
    evaluate_batch_procurement,
)
from simulator.sale import evaluate_cash_sale_pricing
from simulator.lease import calculate_lease_price_first, calculate_dynamic_recommended_lease_price
from simulator.exploitation import calculate_effective_monthly_cash
from simulator.portfolio import (
    StrategyType,
    TruckState,
    TruckRecord,
    MonthlyPortfolioSnapshot,
)


@dataclass
class SimulationConfig:
    """Configuration parameters for deterministic monthly portfolio simulation."""
    financing: FinancingAssumptions
    procurement: ProcurementAssumptions
    primary_strategy: StrategyType = StrategyType.LEASING
    strategy_allocation: Optional[Dict[StrategyType, float]] = None
    cash_sale: CashSaleAssumptions = field(default_factory=CashSaleAssumptions)
    lease: LeaseAssumptions = field(default_factory=LeaseAssumptions)
    exploitation: ExploitationAssumptions = field(default_factory=ExploitationAssumptions)
    protection_config: ProtectionCostConfig = field(default_factory=ProtectionCostConfig)
    tax_config: TaxConfig = field(default_factory=TaxConfig)
    horizon_months: int = 36
    reinvest_cash: bool = True  # If True, automatically orders new batches of 5 when affordable above reserve


@dataclass
class SimulationResult:
    """Full trajectory output and summary performance of portfolio simulation."""
    config: SimulationConfig
    snapshots: List[MonthlyPortfolioSnapshot]
    trucks: List[TruckRecord]
    total_trucks_purchased: int
    final_cash: float
    final_debt: float
    minimum_cash_experienced: float
    cumulative_cash_generated: float
    cumulative_debt_service_paid: float
    cumulative_reinvestment_deployed: float
    reinvestment_batch_count: int
    summary_metrics: Dict[str, Any]


def run_portfolio_simulation(config: SimulationConfig) -> SimulationResult:
    """Execute monthly discrete event portfolio simulation deterministically (Section 11).
    
    1. Start with opening cash and opening bank debt.
    2. Receive scheduled lease deposits/installments and exploitation cash flow.
    3. Pay operating expenses and recurring protection costs.
    4. Pay the bank loan installment.
    5. Record sale proceeds when a truck is sold.
    6. Update lease receivables and outstanding balances.
    7. Compute closing cash before reinvestment.
    8. Check whether another complete procurement batch is affordable after maintaining cash reserve.
    9. If yes, purchase exactly the largest affordable multiple of batch step; if no, wait.
    10. Record portfolio KPIs and continue to next month.
    """
    if config.horizon_months <= 0:
        raise SimulatorValidationError("Horizon months must be positive")

    unit_cost = config.procurement.effective_unit_cost
    batch_step = config.procurement.batch_step
    reserve = config.financing.min_cash_reserve

    # Pre-compute loan amortization schedule
    loan_sched = generate_loan_schedule_from_assumptions(config.financing)
    loan_rows_by_month = {row.month: row for row in loan_sched.rows}

    # Month 0 Initial Capitalization & Initial Batch Procurement
    net_loan_proceeds = max(
        0.0,
        config.financing.bank_loan_amount
        - config.financing.bank_arrangement_fees
        - config.financing.other_bank_charges,
    )
    current_cash = config.financing.starting_cash + net_loan_proceeds
    current_debt = config.financing.bank_loan_amount

    # Initial batch procurement
    initial_truck_count = calculate_purchasable_trucks(
        available_cash=current_cash,
        reserve=reserve,
        unit_cost=unit_cost,
        batch_step=batch_step,
    )

    trucks: List[TruckRecord] = []
    truck_id_counter = 1

    initial_procurement_expenditure = initial_truck_count * unit_cost
    current_cash -= initial_procurement_expenditure

    # Instantiate Initial Batch Trucks
    initial_deposit_cash = 0.0
    for _ in range(initial_truck_count):
        strat = config.primary_strategy
        if strat == StrategyType.LEASING:
            # Lease term and deposit
            term = config.lease.term_months
            dep = config.lease.initial_deposit
            if config.lease.total_contract_price is not None:
                contract_price = config.lease.total_contract_price
            else:
                contract_price = calculate_dynamic_recommended_lease_price(
                    truck_cost=unit_cost,
                    initial_deposit=dep,
                    term_months=term,
                    target_annual_return=config.lease.target_annual_return,
                )
            financed = max(0.0, contract_price - dep)
            installment = financed / float(term) if term > 0 else 0.0

            truck = TruckRecord(
                id=truck_id_counter,
                strategy=StrategyType.LEASING,
                acquisition_month=0,
                acquisition_cost=unit_cost,
                current_state=TruckState.LEASED,
                lease_term_months=term,
                lease_start_month=1,
                monthly_installment=installment,
                remaining_receivable=financed,
            )
            initial_deposit_cash += dep
        elif strat == StrategyType.EXPLOITATION:
            eff_profit = calculate_effective_monthly_cash(
                net_monthly_profit=config.exploitation.net_monthly_profit_per_truck,
                downtime_rate=config.exploitation.downtime_allowance_rate,
                gps_monthly_cost=config.exploitation.gps_monthly_cost,
                other_overhead=config.exploitation.other_monthly_overhead,
            )
            truck = TruckRecord(
                id=truck_id_counter,
                strategy=StrategyType.EXPLOITATION,
                acquisition_month=0,
                acquisition_cost=unit_cost,
                current_state=TruckState.EXPLOITATION_ACTIVE,
                net_monthly_profit=eff_profit,
            )
        else:  # CASH_SALE
            sale_pricing = evaluate_cash_sale_pricing(
                landed_cost=unit_cost,
                target_markup=config.cash_sale.target_markup,
                holding_period_months=config.cash_sale.holding_period_months,
                annual_financing_rate=config.financing.annual_financing_rate,
            )
            truck = TruckRecord(
                id=truck_id_counter,
                strategy=StrategyType.CASH_SALE,
                acquisition_month=0,
                acquisition_cost=unit_cost,
                current_state=TruckState.AVAILABLE,
                sale_month=max(1, config.cash_sale.holding_period_months),
                sale_price=sale_pricing.recommended_price,
                holding_period_months=config.cash_sale.holding_period_months,
            )
        trucks.append(truck)
        truck_id_counter += 1

    # Inflow initial lease deposits received upon signing at Month 0
    current_cash += initial_deposit_cash

    snapshots: List[MonthlyPortfolioSnapshot] = []
    cumulative_reinvestment_total = initial_procurement_expenditure
    reinvestment_batch_count = 1 if initial_truck_count > 0 else 0
    minimum_cash_experienced = current_cash

    # Simulation Monthly Steps 1 .. H
    for m in range(1, config.horizon_months + 1):
        opening_cash = current_cash
        opening_debt = current_debt

        inflows_lease_deposits = 0.0
        inflows_lease_installments = 0.0
        inflows_exploitation = 0.0
        inflows_sales = 0.0

        outflows_operating = 0.0
        outflows_protection = 0.0

        # Process active trucks
        for t in trucks:
            if t.strategy == StrategyType.LEASING:
                if t.current_state == TruckState.LEASED and t.lease_start_month is not None and t.lease_term_months is not None:
                    months_active = m - t.lease_start_month + 1
                    if 1 <= months_active <= t.lease_term_months:
                        inst = min(t.monthly_installment, t.remaining_receivable)
                        inflows_lease_installments += inst
                        t.remaining_receivable = max(0.0, t.remaining_receivable - inst)
                        # Recurring protection (e.g. GPS monitoring)
                        outflows_protection += config.protection_config.gps_monthly_sub.amount if config.protection_config.gps_monthly_sub.enabled else 0.0

                        if t.remaining_receivable <= 1.0 or months_active == t.lease_term_months:
                            t.current_state = TruckState.COMPLETED
            elif t.strategy == StrategyType.EXPLOITATION:
                if t.current_state == TruckState.EXPLOITATION_ACTIVE:
                    inflows_exploitation += t.net_monthly_profit
                    # Operational recurring cost deductions if applicable
                    outflows_operating += config.exploitation.gps_monthly_cost + config.exploitation.other_monthly_overhead
            elif t.strategy == StrategyType.CASH_SALE:
                if t.current_state == TruckState.AVAILABLE and t.sale_month == m:
                    inflows_sales += t.sale_price
                    outflows_operating += config.cash_sale.selling_costs + config.cash_sale.transaction_costs
                    t.current_state = TruckState.SOLD

        total_inflows = inflows_lease_deposits + inflows_lease_installments + inflows_exploitation + inflows_sales

        # Debt Service for Month m
        if m in loan_rows_by_month:
            debt_row = loan_rows_by_month[m]
            outflows_debt_principal = debt_row.principal
            outflows_debt_interest = debt_row.interest
            outflows_debt_service = debt_row.payment
            current_debt = debt_row.closing_balance
        else:
            outflows_debt_principal = 0.0
            outflows_debt_interest = 0.0
            outflows_debt_service = 0.0
            current_debt = 0.0

        total_outflows = outflows_operating + outflows_protection + outflows_debt_service

        cash_before_reinvestment = opening_cash + total_inflows - total_outflows

        # Step 8 & 9: Discrete Batch Reinvestment Evaluation
        reinvest_trucks = 0
        reinvest_cost = 0.0

        if config.reinvest_cash and cash_before_reinvestment > reserve:
            reinvest_trucks = calculate_purchasable_trucks(
                available_cash=cash_before_reinvestment,
                reserve=reserve,
                unit_cost=unit_cost,
                batch_step=batch_step,
            )

        if reinvest_trucks > 0:
            reinvest_cost = reinvest_trucks * unit_cost
            cash_before_reinvestment -= reinvest_cost
            cumulative_reinvestment_total += reinvest_cost
            reinvestment_batch_count += 1

            # Instantiate newly acquired trucks
            for _ in range(reinvest_trucks):
                strat = config.primary_strategy
                if strat == StrategyType.LEASING:
                    term = config.lease.term_months
                    dep = config.lease.initial_deposit
                    contract_price = calculate_dynamic_recommended_lease_price(
                        truck_cost=unit_cost,
                        initial_deposit=dep,
                        term_months=term,
                        target_annual_return=config.lease.target_annual_return,
                    )
                    financed = max(0.0, contract_price - dep)
                    installment = financed / float(term) if term > 0 else 0.0

                    # Deposit received immediately upon acquisition
                    inflows_lease_deposits += dep
                    total_inflows += dep
                    cash_before_reinvestment += dep

                    new_truck = TruckRecord(
                        id=truck_id_counter,
                        strategy=StrategyType.LEASING,
                        acquisition_month=m,
                        acquisition_cost=unit_cost,
                        current_state=TruckState.LEASED,
                        lease_term_months=term,
                        lease_start_month=m + 1,  # First payment due next month
                        monthly_installment=installment,
                        remaining_receivable=financed,
                    )
                elif strat == StrategyType.EXPLOITATION:
                    eff_profit = calculate_effective_monthly_cash(
                        net_monthly_profit=config.exploitation.net_monthly_profit_per_truck,
                        downtime_rate=config.exploitation.downtime_allowance_rate,
                        gps_monthly_cost=config.exploitation.gps_monthly_cost,
                        other_overhead=config.exploitation.other_monthly_overhead,
                    )
                    new_truck = TruckRecord(
                        id=truck_id_counter,
                        strategy=StrategyType.EXPLOITATION,
                        acquisition_month=m,
                        acquisition_cost=unit_cost,
                        current_state=TruckState.EXPLOITATION_ACTIVE,
                        net_monthly_profit=eff_profit,
                    )
                else:  # CASH_SALE
                    sale_pricing = evaluate_cash_sale_pricing(
                        landed_cost=unit_cost,
                        target_markup=config.cash_sale.target_markup,
                        holding_period_months=config.cash_sale.holding_period_months,
                        annual_financing_rate=config.financing.annual_financing_rate,
                    )
                    new_truck = TruckRecord(
                        id=truck_id_counter,
                        strategy=StrategyType.CASH_SALE,
                        acquisition_month=m,
                        acquisition_cost=unit_cost,
                        current_state=TruckState.AVAILABLE,
                        sale_month=m + max(1, config.cash_sale.holding_period_months),
                        sale_price=sale_pricing.recommended_price,
                        holding_period_months=config.cash_sale.holding_period_months,
                    )
                trucks.append(new_truck)
                truck_id_counter += 1

        closing_cash = cash_before_reinvestment
        current_cash = closing_cash

        if current_cash < minimum_cash_experienced:
            minimum_cash_experienced = current_cash

        # Compute Fleet and Receivable Totals
        total_trucks_owned = len(trucks)
        active_trucks = sum(1 for t in trucks if t.is_active)
        trucks_by_strat = {
            StrategyType.LEASING.value: sum(1 for t in trucks if t.strategy == StrategyType.LEASING),
            StrategyType.EXPLOITATION.value: sum(1 for t in trucks if t.strategy == StrategyType.EXPLOITATION),
            StrategyType.CASH_SALE.value: sum(1 for t in trucks if t.strategy == StrategyType.CASH_SALE),
        }
        outstanding_receivables = sum(
            t.remaining_receivable for t in trucks if t.strategy == StrategyType.LEASING and t.current_state == TruckState.LEASED
        )
        cash_surplus = max(0.0, closing_cash - reserve)
        next_batch_required = (batch_step * unit_cost) + reserve
        next_batch_shortfall = max(0.0, next_batch_required - closing_cash)

        snapshot = MonthlyPortfolioSnapshot(
            month=m,
            opening_cash=opening_cash,
            opening_debt=opening_debt,
            inflows_lease_deposits=inflows_lease_deposits,
            inflows_lease_installments=inflows_lease_installments,
            inflows_exploitation=inflows_exploitation,
            inflows_sales=inflows_sales,
            total_inflows=total_inflows,
            outflows_operating=outflows_operating,
            outflows_protection=outflows_protection,
            outflows_debt_principal=outflows_debt_principal,
            outflows_debt_interest=outflows_debt_interest,
            outflows_debt_service=outflows_debt_service,
            total_outflows=total_outflows,
            cash_before_reinvestment=cash_before_reinvestment + reinvest_cost,
            reinvestment_trucks_purchased=reinvest_trucks,
            reinvestment_cost=reinvest_cost,
            closing_cash=closing_cash,
            closing_debt=current_debt,
            total_trucks_owned=total_trucks_owned,
            active_trucks_count=active_trucks,
            trucks_by_strategy=trucks_by_strat,
            lease_receivables_outstanding=outstanding_receivables,
            cash_reserve_required=reserve,
            cash_surplus_above_reserve=cash_surplus,
            next_batch_shortfall=next_batch_shortfall,
        )
        snapshots.append(snapshot)

    total_debt_service_paid = sum(s.outflows_debt_service for s in snapshots)
    total_cash_inflows = sum(s.total_inflows for s in snapshots)

    summary_metrics = {
        "final_cash": current_cash,
        "final_debt": current_debt,
        "minimum_cash_experienced": minimum_cash_experienced,
        "total_trucks_purchased": len(trucks),
        "total_cash_inflows": total_cash_inflows,
        "total_debt_service_paid": total_debt_service_paid,
        "total_reinvestment_deployed": cumulative_reinvestment_total,
        "reinvestment_batches": reinvestment_batch_count,
        "reserve_preserved": minimum_cash_experienced >= reserve,
    }

    return SimulationResult(
        config=config,
        snapshots=snapshots,
        trucks=trucks,
        total_trucks_purchased=len(trucks),
        final_cash=current_cash,
        final_debt=current_debt,
        minimum_cash_experienced=minimum_cash_experienced,
        cumulative_cash_generated=total_cash_inflows,
        cumulative_debt_service_paid=total_debt_service_paid,
        cumulative_reinvestment_deployed=cumulative_reinvestment_total,
        reinvestment_batch_count=reinvestment_batch_count,
        summary_metrics=summary_metrics,
    )


def simulation_to_dataframe(result: SimulationResult) -> pd.DataFrame:
    """Convert simulation monthly snapshots into a Pandas DataFrame."""
    rows = []
    for s in result.snapshots:
        rows.append({
            "Month": s.month,
            "Opening Cash": s.opening_cash,
            "Opening Debt": s.opening_debt,
            "Lease Deposits": s.inflows_lease_deposits,
            "Lease Installments": s.inflows_lease_installments,
            "Exploitation Cash": s.inflows_exploitation,
            "Sales Proceeds": s.inflows_sales,
            "Total Inflows": s.total_inflows,
            "Debt Service": s.outflows_debt_service,
            "Reinvestment Trucks": s.reinvestment_trucks_purchased,
            "Reinvestment Cost": s.reinvestment_cost,
            "Closing Cash": s.closing_cash,
            "Closing Debt": s.closing_debt,
            "Fleet Size": s.total_trucks_owned,
            "Receivables Outstanding": s.lease_receivables_outstanding,
            "Surplus Above Reserve": s.cash_surplus_above_reserve,
        })
    return pd.DataFrame(rows)
