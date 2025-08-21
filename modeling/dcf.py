import argparse, traceback
import logging
from decimal import Decimal
from pathlib import Path
import sys

# Add project root to path for config access
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from modeling.data import (
    get_EV_statement, 
    get_income_statement, 
    get_cashflow_statement, 
    get_balance_statement
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


def DCF(ticker, ev_statement, income_statement, balance_statement, cashflow_statement, discount_rate, forecast, earnings_growth_rate, cap_ex_growth_rate, perpetual_growth_rate, variable_growth_rates=None):
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
    enterprise_val = enterprise_value(income_statement,
                                        cashflow_statement,
                                        balance_statement,
                                        forecast, 
                                        discount_rate,
                                        earnings_growth_rate, 
                                        cap_ex_growth_rate, 
                                        perpetual_growth_rate,
                                        variable_growth_rates)

    equity_val, share_price = equity_value(enterprise_val,
                                           ev_statement)

    logger.info(f"DCF Results for {ticker}: "
                f"Enterprise Value: ${enterprise_val:.2E}, "
                f"Equity Value: ${equity_val:.2E}, "
                f"Share Price: ${share_price:.2E}")

    return {
        'date': income_statement[0]['date'],       # statement date used
        'enterprise_value': enterprise_val,
        'equity_value': equity_val,
        'share_price': share_price
    }


def historical_DCF(ticker, years, forecast, discount_rate, earnings_growth_rate, cap_ex_growth_rate, perpetual_growth_rate, interval = 'annual', apikey = ''):
    """
    Wrap DCF to fetch DCF values over a historical timeframe, denoted period. 

    args:
        same as DCF, except for
        period: number of years to fetch DCF for

    returns:
        {'date': dcf, ..., 'date', dcf}
    """
    dcfs = {}

    income_statement = get_income_statement(ticker = ticker, period = interval, apikey = apikey)['financials']
    balance_statement = get_balance_statement(ticker = ticker, period = interval, apikey = apikey)['financials']
    cashflow_statement = get_cashflow_statement(ticker = ticker, period = interval, apikey = apikey)['financials']
    enterprise_value_statement = get_EV_statement(ticker = ticker, period = interval, apikey = apikey)['enterpriseValues']

    if interval == 'quarter':
        intervals = years * 4
    else:
        intervals = years

    for interval in range(0, intervals):
        try:
            dcf = DCF(ticker, 
                    enterprise_value_statement[interval],
                    income_statement[interval:interval+2],        # pass year + 1 bc we need change in working capital
                    balance_statement[interval:interval+2],
                    cashflow_statement[interval:interval+2],
                    discount_rate,
                    forecast, 
                    earnings_growth_rate,  
                    cap_ex_growth_rate, 
                    perpetual_growth_rate)
        except (Exception, IndexError) as e:
            logger.warning(f"Interval {interval} unavailable for {ticker}: {traceback.format_exc()}")
        else: dcfs[dcf['date']] = dcf 
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
    return ebit * (1-tax_rate) + non_cash_charges + cwc + cap_ex


def get_discount_rate(equity_beta=None, debt_to_equity=None, tax_rate=None, industry=None):
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
        if industry and hasattr(DCF_CONFIG, 'beta_defaults'):
            beta = DCF_CONFIG.beta_defaults.get(industry, DCF_CONFIG.beta_defaults.get('default', 1.0))
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
        logger.debug(f"Using cost of equity {cost_of_equity:.3f} as WACC proxy (no capital structure data)")
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
    tax_rate = max(DCF_CONFIG.tax_rate_floor, min(tax_rate, DCF_CONFIG.tax_rate_ceiling))
    
    wacc = (equity_weight * cost_of_equity + 
            debt_weight * cost_of_debt * (1 - tax_rate))
    
    logger.debug(f"Calculated WACC: {wacc:.3f} (E/V: {equity_weight:.2f}, D/V: {debt_weight:.2f}, Tax: {tax_rate:.2f})")
    
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
        debt = ev_data['addTotalDebt']
        cash = ev_data['minusCashAndCashEquivalents']
        shares = ev_data['numberOfShares']
    else:
        # Original format
        debt = enterprise_value_statement['+ Total Debt'] 
        cash = enterprise_value_statement['- Cash & Cash Equivalents']
        shares = enterprise_value_statement['Number of Shares']
    
    equity_val = enterprise_value - debt + cash
    share_price = equity_val / float(shares)

    return equity_val, share_price


def enterprise_value(income_statement, cashflow_statement, balance_statement, period, discount_rate, earnings_growth_rate, cap_ex_growth_rate, perpetual_growth_rate, variable_growth_rates=None):
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
    if income_statement[0]['EBIT']:
        ebit = float(income_statement[0]['EBIT'])
    else:
        ebit = float(input(f"EBIT missing. Enter EBIT on {income_statement[0]['date']} or skip: "))
    tax_rate = float(income_statement[0]['Income Tax Expense']) /  \
               float(income_statement[0]['Earnings before Tax'])
    non_cash_charges = float(cashflow_statement[0]['Depreciation & Amortization'])
    cwc = (float(balance_statement[0]['Total assets']) - float(balance_statement[0]['Total non-current assets'])) - \
          (float(balance_statement[1]['Total assets']) - float(balance_statement[1]['Total non-current assets']))
    cap_ex = float(cashflow_statement[0]['Capital Expenditure'])
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
        base_year = int(income_statement[0]['date'][0:4])
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
    logger.info(f'Forecasting flows for {period} years out, starting at {income_statement[0]["date"]}')
    logger.debug('Year   | Growth Rate |     DFCF    |    EBIT     |     D&A     |     CWC     |   CAP_EX    |')
    logger.debug('-' * 88)
    
    # Store initial values for compound growth calculation
    base_ebit = ebit
    base_ncc = non_cash_charges
    base_cwc = cwc
    base_capex = cap_ex
    
    for yr in range(1, period+1):    
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
        PV_flow = flow/((1 + discount)**yr)
        flows.append(PV_flow)

        forecast_year = int(income_statement[0]['date'][0:4]) + yr
        logger.debug(f'{forecast_year} | {year_growth_rate:>9.1%} | {PV_flow:>11.2E} | {ebit:>11.2E} | '
                    f'{non_cash_charges:>11.2E} | {cwc:>11.2E} | {cap_ex:>11.2E} |')

    NPV_FCF = sum(flows)
    
    # now calculate terminal value using perpetual growth rate
    final_cashflow = flows[-1] * (1 + perpetual_growth_rate)
    TV = final_cashflow/(discount - perpetual_growth_rate)
    NPV_TV = TV/(1+discount)**(1+period)

    return NPV_TV+NPV_FCF

