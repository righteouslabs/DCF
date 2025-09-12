import argparse, traceback
import logging
import numpy as np
import pandas as pd
from decimal import Decimal
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import sys

# Add project root to path for config access
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from .data import (
    get_EV_statement,
    get_income_statement,
    get_cashflow_statement,
    get_balance_statement,
    get_comprehensive_historical_data,
)

# Import configuration management
try:
    from config_manager import get_config

    config = get_config()
    DCF_CONFIG = config.forecasting.dcf
except ImportError:
    # Fallback to default values if config not available
    class DCFConfig:
        default_discount_rate = 0.10
        working_capital_decay_rate = 0.7
        risk_free_rate = 0.04
        market_premium = 0.06
        default_earnings_growth_rate = 0.05
        default_capex_growth_rate = 0.045
        terminal_value_method = "gordon_growth"
        max_terminal_growth_rate = 0.04
        min_terminal_growth_rate = 0.02
        tax_rate_floor = 0.15
        tax_rate_ceiling = 0.35
        beta_defaults = {"default": 1.0}

    DCF_CONFIG = DCFConfig()

# Setup DCF module logger
logger = logging.getLogger(__name__)


def DCF(
    ticker,
    ev_statement,
    income_statement,
    balance_statement,
    cashflow_statement,
    discount_rate,
    forecast,
    earnings_growth_rate,
    cap_ex_growth_rate,
    perpetual_growth_rate,
    variable_growth_rates=None,
):
    """
    DCF model with support for variable year-by-year growth rates.

    args:
        ticker: company ticker
        ev_statement: enterprise value statement data
        income_statement: income statement data
        balance_statement: balance sheet data
        cashflow_statement: cash flow statement data
        discount_rate: WACC discount rate
        forecast: number of years to forecast
        earnings_growth_rate: fallback constant earnings growth rate
        cap_ex_growth_rate: fallback constant capex growth rate
        perpetual_growth_rate: terminal growth rate
        variable_growth_rates: dict with year -> growth_rate mapping or list of growth rates
                              e.g., {2025: -0.076, 2026: 0.305, 2027: 0.059, 2028: 0.049, 2029: 0.050}
                              or [-0.076, 0.305, 0.059, 0.049, 0.050, 0.050, 0.050, 0.050, 0.050, 0.050]

    returns:
        dict: {'share price': __, 'enterprise_value': __, 'equity_value': __, 'date': __}
    """
    enterprise_val = enterprise_value(
        income_statement,
        cashflow_statement,
        balance_statement,
        forecast,
        discount_rate,
        earnings_growth_rate,
        cap_ex_growth_rate,
        perpetual_growth_rate,
        variable_growth_rates,
    )

    equity_val, share_price = equity_value(enterprise_val, ev_statement)

    logger.info(
        f"DCF Results for {ticker}: "
        f"Enterprise Value: ${enterprise_val:.2E}, "
        f"Equity Value: ${equity_val:.2E}, "
        f"Share Price: ${share_price:.2E}"
    )

    return {
        "date": income_statement[0]["date"],  # statement date used
        "enterprise_value": enterprise_val,
        "equity_value": equity_val,
        "share_price": share_price,
    }


def historical_DCF(
    ticker,
    years,
    forecast,
    discount_rate,
    earnings_growth_rate,
    cap_ex_growth_rate,
    perpetual_growth_rate,
    interval="annual",
):
    """
    Wrap DCF to fetch DCF values over a historical timeframe, denoted period.

    args:
        same as DCF, except for
        period: number of years to fetch DCF for

    returns:
        {'date': dcf, ..., 'date', dcf}
    """
    dcfs = {}

    income_statement = get_income_statement(ticker=ticker, period=interval)[
        "financials"
    ]
    balance_statement = get_balance_statement(ticker=ticker, period=interval)[
        "financials"
    ]
    cashflow_statement = get_cashflow_statement(ticker=ticker, period=interval)[
        "financials"
    ]
    enterprise_value_statement = get_EV_statement(ticker=ticker, period=interval)[
        "enterpriseValues"
    ]

    if interval == "quarter":
        intervals = years * 4
    else:
        intervals = years

    for interval in range(0, intervals):
        try:
            dcf = DCF(
                ticker,
                enterprise_value_statement[interval],
                income_statement[
                    interval : interval + 2
                ],  # pass year + 1 bc we need change in working capital
                balance_statement[interval : interval + 2],
                cashflow_statement[interval : interval + 2],
                discount_rate,
                forecast,
                earnings_growth_rate,
                cap_ex_growth_rate,
                perpetual_growth_rate,
            )
        except (Exception, IndexError) as e:
            logger.warning(
                f"Interval {interval} unavailable for {ticker}: {traceback.format_exc()}"
            )
        else:
            dcfs[dcf["date"]] = dcf
        logger.debug("-" * 60)

    return dcfs


def ulFCF(ebit, tax_rate, non_cash_charges, cwc, cap_ex):
    """
    Formula to derive unlevered free cash flow to firm. Used in forecasting.

    args:
        ebit: Earnings before interest payments and taxes.
        tax_rate: The tax rate a firm is expected to pay. Usually a company's historical effective rate.
        non_cash_charges: Depreciation and amortization costs.
        cwc: Annual change in net working capital.
        cap_ex: capital expenditures, or what is spent to maintain zgrowth rate.

    returns:
        unlevered free cash flow
    """
    return ebit * (1 - tax_rate) + non_cash_charges + cwc + cap_ex


def get_discount_rate(
    equity_beta=None, debt_to_equity=None, tax_rate=None, industry=None
):
    """
    Calculate the Weighted Average Cost of Capital (WACC) for a company.
    Uses industry defaults and CAPM when specific data is unavailable.

    args:
        equity_beta: Company's equity beta (risk relative to market)
        debt_to_equity: Debt-to-equity ratio for capital structure
        tax_rate: Corporate tax rate for tax shield calculation
        industry: Industry for beta defaults if equity_beta not provided

    returns:
        Calculated WACC (Weighted Average Cost of Capital)
    """
    # Use configured defaults
    risk_free_rate = DCF_CONFIG.risk_free_rate
    market_premium = DCF_CONFIG.market_premium

    # Determine beta
    if equity_beta is None:
        if industry and hasattr(DCF_CONFIG, "beta_defaults"):
            beta = DCF_CONFIG.beta_defaults.get(
                industry, DCF_CONFIG.beta_defaults.get("default", 1.0)
            )
        else:
            beta = 1.0  # Market beta default
        logger.debug(f"Using default beta {beta} for industry: {industry}")
    else:
        beta = equity_beta
        logger.debug(f"Using provided beta: {beta}")

    # Calculate cost of equity using CAPM
    cost_of_equity = risk_free_rate + beta * market_premium

    # If no capital structure info, return cost of equity as proxy
    if debt_to_equity is None or tax_rate is None:
        logger.debug(
            f"Using cost of equity {cost_of_equity:.3f} as WACC proxy (no capital structure data)"
        )
        return cost_of_equity

    # Calculate WACC with capital structure
    # Cost of debt approximation (risk-free + spread based on leverage)
    debt_spread = min(0.05, debt_to_equity * 0.02)  # Max 5% spread
    cost_of_debt = risk_free_rate + debt_spread

    # WACC formula: E/V * Cost_of_Equity + D/V * Cost_of_Debt * (1 - Tax_Rate)
    total_value = 1 + debt_to_equity  # E + D
    equity_weight = 1 / total_value
    debt_weight = debt_to_equity / total_value

    # Bound tax rate
    tax_rate = max(
        DCF_CONFIG.tax_rate_floor, min(tax_rate, DCF_CONFIG.tax_rate_ceiling)
    )

    wacc = equity_weight * cost_of_equity + debt_weight * cost_of_debt * (1 - tax_rate)

    logger.debug(
        f"Calculated WACC: {wacc:.3f} (E/V: {equity_weight:.2f}, D/V: {debt_weight:.2f}, Tax: {tax_rate:.2f})"
    )

    return wacc


def equity_value(enterprise_value, enterprise_value_statement):
    """
    Given an enterprise value, return the equity value by adjusting for cash/cash equivs. and total debt.

    args:
        enterprise_value: (EV = market cap + total debt - cash), or total value
        enterprise_value_statement: information on debt & cash (list or dict format)

    returns:
        equity_value: (enterprise value - debt + cash)
        share_price: equity value/shares outstanding
    """
    # Handle both old dict format and new FMP API list format
    if isinstance(enterprise_value_statement, list):
        # FMP API format - use most recent data
        ev_data = enterprise_value_statement[0]
        debt = ev_data["addTotalDebt"]
        cash = ev_data["minusCashAndCashEquivalents"]
        shares = ev_data["numberOfShares"]
    else:
        # Original format
        debt = enterprise_value_statement["+ Total Debt"]
        cash = enterprise_value_statement["- Cash & Cash Equivalents"]
        shares = enterprise_value_statement["Number of Shares"]

    equity_val = enterprise_value - debt + cash
    share_price = equity_val / float(shares)

    return equity_val, share_price


def enterprise_value(
    income_statement,
    cashflow_statement,
    balance_statement,
    period,
    discount_rate,
    earnings_growth_rate,
    cap_ex_growth_rate,
    perpetual_growth_rate,
    variable_growth_rates=None,
):
    """
    Calculate enterprise value by NPV of explicit _period_ free cash flows + NPV of terminal value,
    both discounted by W.A.C.C. Now supports variable year-by-year growth rates.

    args:
        income_statement: income statement data
        cashflow_statement: cash flow statement data
        balance_statement: balance sheet data
        period: years into the future
        earnings_growth_rate: fallback constant earnings growth rate, YoY
        cap_ex_growth_rate: fallback constant cap_ex growth rate, YoY
        perpetual_growth_rate: assumed growth rate in perpetuity for terminal value, YoY
        variable_growth_rates: dict with year -> growth_rate mapping or list of growth rates

    returns:
        enterprise value
    """
    # XXX: statements are returned as historical list, 0 most recent
    if income_statement[0].get("operatingIncome"):
        ebit = float(income_statement[0]["operatingIncome"])
    elif income_statement[0].get("EBIT"):
        ebit = float(income_statement[0]["EBIT"])
    else:
        ebit = float(
            input(
                f"EBIT missing. Enter EBIT on {income_statement[0]['date']} or skip: "
            )
        )
    tax_rate = float(income_statement[0]["incomeTaxExpense"]) / float(
        income_statement[0]["incomeBeforeTax"]
    )
    non_cash_charges = float(cashflow_statement[0]["depreciationAndAmortization"])
    cwc = (
        float(balance_statement[0]["totalAssets"])
        - float(balance_statement[0]["totalNonCurrentAssets"])
    ) - (
        float(balance_statement[1]["totalAssets"])
        - float(balance_statement[1]["totalNonCurrentAssets"])
    )
    cap_ex = float(cashflow_statement[0]["capitalExpenditure"])
    discount = discount_rate

    # Prepare growth rates for variable growth support
    if variable_growth_rates is None:
        # Use constant growth rates from config or parameters
        if earnings_growth_rate is None:
            earnings_growth_rate = DCF_CONFIG.default_earnings_growth_rate
        if cap_ex_growth_rate is None:
            cap_ex_growth_rate = DCF_CONFIG.default_capex_growth_rate

        growth_rates = [earnings_growth_rate] * period
        cap_ex_growth_rates = [cap_ex_growth_rate] * period
    elif isinstance(variable_growth_rates, dict):
        # Convert dict to list based on years
        base_year = int(income_statement[0]["date"][0:4])
        growth_rates = []
        cap_ex_growth_rates = []
        for i in range(period):
            year = base_year + i + 1
            gr = variable_growth_rates.get(year, earnings_growth_rate)
            growth_rates.append(gr)
            cap_ex_growth_rates.append(gr)  # Use same rate for cap_ex
    elif isinstance(variable_growth_rates, list):
        # Use provided list, extend with constant rate if needed
        growth_rates = variable_growth_rates.copy()
        while len(growth_rates) < period:
            growth_rates.append(earnings_growth_rate)
        growth_rates = growth_rates[:period]  # Trim if too long
        cap_ex_growth_rates = growth_rates.copy()  # Use same rates for cap_ex
    else:
        raise ValueError("variable_growth_rates must be dict, list, or None")

    flows = []

    # Now let's iterate through years to calculate FCF, starting with most recent year
    logger.info(
        f'Forecasting flows for {period} years out, starting at {income_statement[0]["date"]}'
    )
    logger.debug(
        "Year   | Growth Rate |     DFCF    |    EBIT     |     D&A     |     CWC     |   CAP_EX    |"
    )
    logger.debug("-" * 88)

    # Store initial values for compound growth calculation
    base_ebit = ebit
    base_ncc = non_cash_charges
    base_cwc = cwc
    base_capex = cap_ex

    for yr in range(1, period + 1):
        # Get growth rate for this year
        year_growth_rate = growth_rates[yr - 1]
        year_capex_growth_rate = cap_ex_growth_rates[yr - 1]

        # Apply variable growth rates (compound growth from base year)
        if yr == 1:
            ebit = base_ebit * (1 + year_growth_rate)
            non_cash_charges = base_ncc * (1 + year_growth_rate)
            cap_ex = base_capex * (1 + year_capex_growth_rate)
        else:
            # Compound growth from previous year
            ebit = ebit * (1 + year_growth_rate)
            non_cash_charges = non_cash_charges * (1 + year_growth_rate)
            cap_ex = cap_ex * (1 + year_capex_growth_rate)

        # Apply working capital decay rate from configuration
        # This models the expectation that working capital changes moderate over time
        cwc = cwc * DCF_CONFIG.working_capital_decay_rate  # Configurable decay rate

        # discount by WACC
        flow = ulFCF(ebit, tax_rate, non_cash_charges, cwc, cap_ex)
        PV_flow = flow / ((1 + discount) ** yr)
        flows.append(PV_flow)

        forecast_year = int(income_statement[0]["date"][0:4]) + yr
        logger.debug(
            f"{forecast_year} | {year_growth_rate:>9.1%} | {PV_flow:>11.2E} | {ebit:>11.2E} | "
            f"{non_cash_charges:>11.2E} | {cwc:>11.2E} | {cap_ex:>11.2E} |"
        )

    NPV_FCF = sum(flows)

    # now calculate terminal value using perpetual growth rate
    final_cashflow = flows[-1] * (1 + perpetual_growth_rate)
    TV = final_cashflow / (discount - perpetual_growth_rate)
    NPV_TV = TV / (1 + discount) ** (1 + period)

    return NPV_TV + NPV_FCF


def analyze_growth_trends(historical_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze historical data to extract growth patterns and trends.
    Migrated from generalized_dcf_forecaster.py to enhance DCF submodule.

    Args:
        historical_data: Historical financial data from get_comprehensive_historical_data

    Returns:
        Dictionary containing growth trends and base metrics
    """
    if not historical_data or not historical_data.get("yearly_metrics"):
        raise ValueError("No historical data available")

    metrics = historical_data["yearly_metrics"]
    df = pd.DataFrame(metrics)
    df = df.sort_values("year")

    trends = {}

    # Calculate compound annual growth rates (CAGR) for key metrics
    years = len(df)
    if years < 2:
        logger.warning("Insufficient data for trend analysis")
        return _create_fallback_trends(df.iloc[-1])

    first_year = df.iloc[0]
    last_year = df.iloc[-1]

    # Revenue growth analysis
    if (
        first_year.get("revenue")
        and last_year.get("revenue")
        and first_year["revenue"] > 0
    ):
        revenue_cagr = (last_year["revenue"] / first_year["revenue"]) ** (
            1 / (years - 1)
        ) - 1
        trends["revenue_cagr"] = revenue_cagr
    else:
        trends["revenue_cagr"] = 0.05  # Default 5% growth

    # EBITDA growth analysis
    if (
        first_year.get("ebitda")
        and last_year.get("ebitda")
        and first_year["ebitda"] > 0
    ):
        ebitda_cagr = (last_year["ebitda"] / first_year["ebitda"]) ** (
            1 / (years - 1)
        ) - 1
        trends["ebitda_cagr"] = ebitda_cagr
    else:
        trends["ebitda_cagr"] = trends["revenue_cagr"]  # Follow revenue growth

    # FCFE growth analysis
    if first_year.get("fcfe") and last_year.get("fcfe") and first_year["fcfe"] > 0:
        fcfe_cagr = (last_year["fcfe"] / first_year["fcfe"]) ** (1 / (years - 1)) - 1
        trends["fcfe_cagr"] = fcfe_cagr
    else:
        trends["fcfe_cagr"] = trends["ebitda_cagr"]  # Follow EBITDA growth

    # Calculate recent trends (last 3 years) for better near-term accuracy
    if years >= 3:
        recent_df = df.tail(3)
        recent_revenue_growth = _calculate_period_growth_rates(recent_df, "revenue")
        recent_ebitda_growth = _calculate_period_growth_rates(recent_df, "ebitda")
        recent_fcfe_growth = _calculate_period_growth_rates(recent_df, "fcfe")

        trends["recent_revenue_growth"] = (
            np.mean(recent_revenue_growth)
            if recent_revenue_growth
            else trends["revenue_cagr"]
        )
        trends["recent_ebitda_growth"] = (
            np.mean(recent_ebitda_growth)
            if recent_ebitda_growth
            else trends["ebitda_cagr"]
        )
        trends["recent_fcfe_growth"] = (
            np.mean(recent_fcfe_growth) if recent_fcfe_growth else trends["fcfe_cagr"]
        )
    else:
        trends["recent_revenue_growth"] = trends["revenue_cagr"]
        trends["recent_ebitda_growth"] = trends["ebitda_cagr"]
        trends["recent_fcfe_growth"] = trends["fcfe_cagr"]

    # Extract base year metrics for projections
    latest = df.iloc[-1]
    trends.update(
        {
            "base_year": latest.get("year", datetime.now().year - 1),
            "base_revenue": latest.get("revenue", 0),
            "base_ebitda": latest.get("ebitda", 0),
            "base_fcfe": latest.get("fcfe", 0),
            "base_shares": latest.get("shares_outstanding", 1000000000),  # 1B default
            "base_capex": latest.get("capex", 0),
            "base_debt": latest.get("debt", 0),
            "base_enterprise_value": latest.get("enterprise_value", 0),
            "base_ev_ebitda": latest.get("ev_ebitda_ratio", 15.0),
            "base_ebitda_margin": (
                latest.get("ebitda", 0) / latest.get("revenue", 1)
                if latest.get("revenue")
                else 0.15
            ),
        }
    )

    # Calculate volatility and consistency metrics
    trends["revenue_volatility"] = np.std(_calculate_period_growth_rates(df, "revenue"))
    trends["ebitda_volatility"] = np.std(_calculate_period_growth_rates(df, "ebitda"))
    trends["fcfe_volatility"] = np.std(_calculate_period_growth_rates(df, "fcfe"))

    # Apply business context adjustments
    trends = _apply_business_context_adjustments(trends, latest)

    logger.info(f"📊 Historical trend analysis complete:")
    logger.info(f"   • Revenue CAGR: {trends.get('revenue_cagr', 0):.1%}")
    logger.info(f"   • EBITDA CAGR: {trends.get('ebitda_cagr', 0):.1%}")
    logger.info(f"   • FCFE CAGR: {trends.get('fcfe_cagr', 0):.1%}")
    logger.info(
        f"   • Recent Revenue Growth: {trends.get('recent_revenue_growth', 0):.1%}"
    )

    return trends


def _calculate_period_growth_rates(df: pd.DataFrame, metric: str) -> List[float]:
    """Calculate period-over-period growth rates for a metric"""
    growth_rates = []
    for i in range(1, len(df)):
        current = df.iloc[i].get(metric, 0)
        previous = df.iloc[i - 1].get(metric, 0)

        if previous and previous != 0 and current:
            growth_rate = (current - previous) / abs(previous)
            growth_rates.append(growth_rate)

    return growth_rates


def _create_fallback_trends(latest_metrics: pd.Series) -> Dict[str, Any]:
    """Create fallback trend analysis when insufficient data"""
    return {
        "revenue_cagr": 0.05,
        "ebitda_cagr": 0.05,
        "fcfe_cagr": 0.05,
        "recent_revenue_growth": 0.05,
        "recent_ebitda_growth": 0.05,
        "recent_fcfe_growth": 0.05,
        "base_year": latest_metrics.get("year", datetime.now().year - 1),
        "base_revenue": latest_metrics.get("revenue", 0),
        "base_ebitda": latest_metrics.get("ebitda", 0),
        "base_fcfe": latest_metrics.get("fcfe", 0),
        "base_shares": latest_metrics.get("shares_outstanding", 1000000000),
        "base_capex": latest_metrics.get("capex", 0),
        "base_debt": latest_metrics.get("debt", 0),
        "base_enterprise_value": latest_metrics.get("enterprise_value", 0),
        "base_ev_ebitda": latest_metrics.get("ev_ebitda_ratio", 15.0),
        "base_ebitda_margin": 0.15,
        "revenue_volatility": 0.1,
        "ebitda_volatility": 0.15,
        "fcfe_volatility": 0.2,
    }


def _apply_business_context_adjustments(
    trends: Dict[str, Any], latest: pd.Series
) -> Dict[str, Any]:
    """Apply business context adjustments based on company size and industry characteristics"""

    # Size-based adjustments (larger companies typically have more stable, lower growth)
    revenue = latest.get("revenue", 0)
    if revenue > 100_000_000_000:  # >$100B revenue = mature large cap
        trends["maturity_factor"] = 0.7  # Reduce growth expectations
    elif revenue > 10_000_000_000:  # >$10B revenue = established company
        trends["maturity_factor"] = 0.85
    else:  # Smaller companies
        trends["maturity_factor"] = 1.0

    # Apply maturity adjustments to growth rates
    for growth_key in [
        "revenue_cagr",
        "ebitda_cagr",
        "fcfe_cagr",
        "recent_revenue_growth",
        "recent_ebitda_growth",
        "recent_fcfe_growth",
    ]:
        if growth_key in trends:
            trends[growth_key] *= trends["maturity_factor"]

    # Debt level adjustments (high debt constrains growth)
    debt_to_ebitda = latest.get("debt", 0) / max(latest.get("ebitda", 1), 1)
    if debt_to_ebitda > 4.0:  # High debt
        trends["debt_constraint_factor"] = 0.8
    elif debt_to_ebitda > 2.0:  # Moderate debt
        trends["debt_constraint_factor"] = 0.9
    else:  # Low debt
        trends["debt_constraint_factor"] = 1.0

    return trends


def enhanced_DCF_with_trends(
    ticker,
    years_back=10,
    forecast_years=10,
    discount_rate=None,
    perpetual_growth_rate=0.025,
) -> Dict[str, Any]:
    """
    Enhanced DCF analysis with trend analysis and comprehensive output.
    This combines the original DCF functionality with generalized_dcf_forecaster capabilities.

    Args:
        ticker: Stock ticker symbol
        years_back: Years of historical data for trend analysis
        forecast_years: Years to forecast
        discount_rate: WACC (calculated dynamically if None)
        perpetual_growth_rate: Terminal growth rate

    Returns:
        Comprehensive DCF analysis with trends and projections
    """
    ticker = ticker.upper()
    logger.info(f"🚀 Starting enhanced DCF analysis for {ticker}")

    try:
        # Step 1: Fetch comprehensive historical data
        historical_data = get_comprehensive_historical_data(ticker, years_back)

        if "error" in historical_data:
            raise Exception(f"Data fetch failed: {historical_data['error']}")

        # Step 2: Analyze trends
        trends = analyze_growth_trends(historical_data)

        # Step 3: Calculate dynamic WACC if not provided
        if discount_rate is None:
            discount_rate = get_discount_rate(
                debt_to_equity=trends.get("base_debt", 0)
                / max(trends.get("base_ebitda", 1) * 15, 1),
                tax_rate=0.21,
                industry="default",
            )

        # Step 4: Prepare variable growth rates
        variable_growth_rates = _create_variable_growth_schedule(trends, forecast_years)

        # Step 5: Run DCF using existing submodule functions
        # Use most recent financial data for DCF calculation
        income_data = get_income_statement(ticker, "annual", limit=2)
        balance_data = get_balance_statement(ticker, "annual", limit=2)
        cashflow_data = get_cashflow_statement(ticker, "annual", limit=2)
        ev_data = get_EV_statement(ticker, "annual")["enterpriseValues"]

        # Run DCF calculation
        dcf_result = DCF(
            ticker=ticker,
            ev_statement=ev_data,
            income_statement=income_data.get("financials", [{}])[:2],
            balance_statement=balance_data.get("financials", [{}])[:2],
            cashflow_statement=cashflow_data.get("financials", [{}])[:2],
            discount_rate=discount_rate,
            forecast=forecast_years,
            earnings_growth_rate=trends["revenue_cagr"],
            cap_ex_growth_rate=trends.get(
                "capex_growth_rate", trends["revenue_cagr"] * 0.8
            ),
            perpetual_growth_rate=perpetual_growth_rate,
            variable_growth_rates=variable_growth_rates,
        )

        # Step 6: Calculate IRR based on DCF results
        current_price = dcf_result.get("share_price", 0)
        enterprise_value = dcf_result.get("enterprise_value", 0)
        equity_value = dcf_result.get("equity_value", 0)
        
        # Calculate IRR using projected cash flows
        irr = 0
        npv = 0
        try:
            if current_price > 0 and enterprise_value > 0:
                # Estimate annual free cash flows based on enterprise value and growth
                base_fcf = enterprise_value * discount_rate  # Rough estimate of current FCF
                
                # Project cash flows using variable growth rates
                projected_cash_flows = []
                for i, growth_rate in enumerate(variable_growth_rates):
                    year_fcf = base_fcf * (1 + growth_rate) ** (i + 1)
                    projected_cash_flows.append(year_fcf)
                
                # Terminal value based on final year FCF and terminal growth
                terminal_fcf = projected_cash_flows[-1] * (1 + perpetual_growth_rate)
                terminal_value = terminal_fcf / (discount_rate - perpetual_growth_rate)
                
                # Calculate IRR
                irr = calculate_irr(current_price * trends.get("base_shares", 1), projected_cash_flows, terminal_value)
                
                # Calculate NPV (positive means undervalued)
                npv = sum(cf / (1 + discount_rate) ** (i + 1) for i, cf in enumerate(projected_cash_flows))
                npv += terminal_value / (1 + discount_rate) ** forecast_years
                npv -= current_price * trends.get("base_shares", 1)
                
        except (ValueError, ZeroDivisionError, OverflowError) as e:
            logger.debug(f"IRR calculation failed: {e}")
            irr = discount_rate  # Fallback to discount rate
            npv = 0
        
        # Step 7: Generate comprehensive output
        return {
            "ticker": ticker,
            "analysis_date": datetime.now().isoformat(),
            "data_source": historical_data.get("data_source", "enhanced_dcf"),
            "years_analyzed": len(historical_data.get("yearly_metrics", [])),
            "forecast_years": forecast_years,
            # Trend Analysis
            "trend_analysis": trends,
            "variable_growth_rates": variable_growth_rates,
            # DCF Results with IRR and NPV
            "dcf_valuation": {
                **dcf_result,
                "irr": irr,
                "npv": npv,
                "terminal_value": terminal_value if 'terminal_value' in locals() else 0,
                "projected_cash_flows": projected_cash_flows if 'projected_cash_flows' in locals() else [],
            },
            "discount_rate": discount_rate,
            "terminal_growth_rate": perpetual_growth_rate,
            # Enhanced Metrics
            "enhanced_metrics": {
                "revenue_cagr": trends["revenue_cagr"],
                "ebitda_cagr": trends["ebitda_cagr"],
                "fcfe_cagr": trends["fcfe_cagr"],
                "intrinsic_value": dcf_result.get("share_price", 0),
                "enterprise_value": dcf_result.get("enterprise_value", 0),
                "equity_value": dcf_result.get("equity_value", 0),
                "irr": irr,  # Add IRR to enhanced metrics too
                "npv": npv,  # Add NPV to enhanced metrics
            },
            # Raw Data
            "historical_data": historical_data,
        }

    except Exception as e:
        logger.error(f"❌ Enhanced DCF analysis failed for {ticker}: {e}")
        return {
            "ticker": ticker,
            "error": str(e),
            "analysis_date": datetime.now().isoformat(),
        }


def calculate_irr(initial_investment: float, cash_flows: List[float], terminal_value: float) -> float:
    """Calculate Internal Rate of Return (IRR) using Newton-Raphson method"""
    if initial_investment <= 0:
        return 0
    
    # Combine cash flows with terminal value
    all_cash_flows = [-initial_investment] + cash_flows[:-1] + [cash_flows[-1] + terminal_value]
    
    def npv(rate):
        """Calculate NPV for given rate"""
        return sum(cf / (1 + rate) ** i for i, cf in enumerate(all_cash_flows))
    
    def npv_derivative(rate):
        """Calculate derivative of NPV for Newton-Raphson"""
        return sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(all_cash_flows))
    
    # Newton-Raphson iteration
    rate = 0.1  # Initial guess: 10%
    tolerance = 1e-6
    max_iterations = 100
    
    for _ in range(max_iterations):
        try:
            npv_value = npv(rate)
            npv_deriv = npv_derivative(rate)
            
            if abs(npv_value) < tolerance:
                break
                
            if abs(npv_deriv) < 1e-12:  # Avoid division by zero
                break
                
            new_rate = rate - npv_value / npv_deriv
            
            # Apply bounds to prevent unrealistic rates
            new_rate = max(-0.99, min(new_rate, 5.0))  # Between -99% and 500%
            
            if abs(new_rate - rate) < tolerance:
                break
                
            rate = new_rate
            
        except (ZeroDivisionError, OverflowError):
            break
    
    # Return reasonable IRR or 0 if calculation failed
    return rate if -0.5 <= rate <= 2.0 else 0


def _create_variable_growth_schedule(
    trends: Dict[str, Any], forecast_years: int
) -> List[float]:
    """Create variable growth rate schedule from trends"""
    growth_schedule = []

    # First 3 years: use recent growth with gradual transition
    recent_growth = trends["recent_revenue_growth"]
    long_term_growth = trends["revenue_cagr"]

    for i in range(forecast_years):
        if i < 3:  # First 3 years
            weight = (3 - i) / 3
            growth = recent_growth * weight + long_term_growth * (1 - weight)
        elif i < forecast_years - 2:  # Middle years
            growth = long_term_growth
        else:  # Final 2 years: transition to terminal
            weight = (forecast_years - 1 - i) / 2
            growth = long_term_growth * weight + 0.025 * (1 - weight)

        # Apply business context adjustments
        growth *= trends.get("maturity_factor", 1.0)
        growth *= trends.get("debt_constraint_factor", 1.0)

        # Apply reasonable bounds
        growth = max(growth, -0.1)  # Floor at -10%
        growth = min(growth, 0.5)  # Cap at 50%

        growth_schedule.append(growth)

    return growth_schedule
