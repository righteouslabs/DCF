"""
author: Hugh Alessi
date: Saturday, July 27, 2019  8:25:00 PM
description: Use primitive underlying DCF modeling to compare intrinsic per share price
    to current share price. 

future goals: 
    -- Formalize sensitivity analysis. 
    -- More robust revenue forecasts in FCF. 
    -- EBITA multiples terminal value calculation.
    -- More to be added.
"""


import argparse
import os

from modeling.dcf import historical_DCF
from visualization.plot import visualize_bulk_historicals
from visualization.printouts import prettyprint
# Logging setup
from logging_config import get_logger, log_progress

logger = get_logger(__name__)



def main(args):
    """
    although the if statements are less than desirable, it allows rapid exploration of 
    historical or present DCF values for either a single or list of tickers.
    """

    if args.s > 0:
        if args.v is not None:
            if args.v == 'eg' or 'earnings_growth_rate':
                cond, dcfs = run_setup(args, variable = 'eg')
            elif args.v == 'cg' or 'cap_ex_growth_rate':
                cond, dcfs = run_setup(args, variable = 'cg')
            elif args.v == 'pg' or 'perpetual_growth_rate':
                cond, dcfs = run_setup(args, variable = 'pg')
            elif args.v == 'discount_rate' or 'discount':
                cond, dcfs = run_setup(args, variable = 'discount')
            else:
                # Enhanced dynamic parameter handling
                valid_variables = ['earnings_growth_rate', 'eg', 'cap_ex_growth_rate', 'cg', 
                                 'perpetual_growth_rate', 'pg', 'discount_rate', 'discount']
                raise ValueError(f'Invalid variable "{args.v}". Valid options: {valid_variables}')
        else:
            # should  we just default to something?
            raise ValueError('If step (-- s) is > 0, you must specify the variable via --v. What was passed is invalid.')
    else:
        cond, dcfs = {'Ticker': [args.t]}, {}
        dcfs[args.t] = historical_DCF(args.t, args.y, args.p, args.d, args.eg, args.cg, args.pg, args.i, args.apikey)

    if args.y > 1: # can't graph single timepoint very well....
        visualize_bulk_historicals(dcfs, args.t, cond, args.apikey)
    else:
        prettyprint(dcfs, args.y)


def run_setup(args, variable):
    dcfs, cond = {}, {args.v: []}
    
    for increment in range(1, int(args.steps) + 1): # default to 5 steps?
        # this should probably be wrapped in another function..
        var = vars(args)[variable] * (1 + (args.s * increment))
        step = '{}: {}'.format(args.v, str(var)[0:4])

        cond[args.v].append(step)
        vars(args)[variable] = var
        dcfs[step] = historical_DCF(args.t, args.y, args.p, args.d, args.eg, args.cg, args.pg, args.i, args.apikey)

    return cond, dcfs


def multiple_tickers(tickers, years, forecast_periods, discount_rate, earnings_growth_rate, cap_ex_growth_rate, perpetual_growth_rate, interval='annual', apikey=''):
    """
    Perform DCF analysis for multiple tickers.
    
    args:
        tickers: List of ticker symbols to analyze
        years: Number of historical years for analysis
        forecast_periods: Number of years to forecast
        discount_rate: WACC discount rate
        earnings_growth_rate: Revenue/earnings growth rate
        cap_ex_growth_rate: Capital expenditure growth rate
        perpetual_growth_rate: Terminal growth rate
        interval: 'annual' or 'quarter' for data frequency
        apikey: API key for financial data provider
    
    returns:
        dict: {ticker: dcf_results} for all processed tickers
    """
    logger.info(f"Starting batch DCF analysis for {len(tickers)} tickers")
    
    results = {}
    failed_tickers = []
    
    for ticker in tickers:
        try:
            logger.info(f"Processing {ticker}...")
            
            if years > 1:
                dcf_result = historical_DCF(
                    ticker=ticker,
                    years=years, 
                    forecast=forecast_periods,
                    discount_rate=discount_rate,
                    earnings_growth_rate=earnings_growth_rate,
                    cap_ex_growth_rate=cap_ex_growth_rate,
                    perpetual_growth_rate=perpetual_growth_rate,
                    interval=interval,
                    apikey=apikey
                )
            else:
                # Single period DCF - would need current financial statements
                logger.warning(f"Single-period DCF for {ticker} requires current statement data")
                dcf_result = None
            
            if dcf_result:
                results[ticker] = dcf_result
                logger.info(f"✅ Completed DCF analysis for {ticker}")
            else:
                failed_tickers.append(ticker)
                logger.warning(f"⚠️ No results generated for {ticker}")
                
        except Exception as e:
            failed_tickers.append(ticker)
            logger.error(f"❌ Failed to process {ticker}: {e}")
    
    logger.info(f"Batch DCF completed: {len(results)} successful, {len(failed_tickers)} failed")
    if failed_tickers:
        logger.warning(f"Failed tickers: {failed_tickers}")
    
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--p', '--period', help = 'years to forecast', type = int, default =  5)
    parser.add_argument('--t', '--ticker', help = 'pass a single ticker to do historical DCF', type = str, default = 'AAPL')
    parser.add_argument('--y', '--years', help = 'number of years to compute DCF analysis for', type = int, default = 1)
    parser.add_argument('--i', '--interval', help = 'interval period for each calc, either "annual" or "quarter"', default = 'annual')
    parser.add_argument('--s', '--step_increase', help = 'specify step increase for EG, CG, PG to enable comparisons.', type = float, default = 0)
    parser.add_argument('--steps', help = 'steps to take if --s is > 0', default = 5)
    parser.add_argument('--v', '--variable', help = 'if --step_increase is specified, must specifiy variable to increase from: [earnings_growth_rate, discount_rate]', default = None)
    parser.add_argument('--d', '--discount_rate', help = 'discount rate for future cash flow to firm', default = 0.1)
    parser.add_argument('--eg', '--earnings_growth_rate', help = 'growth in revenue, YoY',  type = float, default = .05)
    parser.add_argument('--cg', '--cap_ex_growth_rate', help = 'growth in cap_ex, YoY', type = float, default = 0.045)
    parser.add_argument('--pg', '--perpetual_growth_rate', help = 'for perpetuity growth terminal value', type = float, default = 0.05)
    parser.add_argument('--apikey', help='API key for financialmodelingprep.com', default=os.environ.get('APIKEY'))

    args = parser.parse_args()
    main(args)
