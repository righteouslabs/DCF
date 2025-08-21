import argparse, traceback
import logging
from decimal import Decimal

from modeling.data import (
    get_EV_statement, 
    get_income_statement, 
    get_cashflow_statement, 
    get_balance_statement
)

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


def get_discount_rate():
    """
    Calculate the Weighted Average Cost of Capital (WACC) for our company.
    Used for consideration of existing capital structure.

    args:
    
    returns:
        W.A.C.C.
    """
    return .1 # TODO: implement 


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
        # Use constant growth rates as before
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
        
        cwc = cwc * 0.7  # TODO: evaluate this cwc rate? 0.1 annually?

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

