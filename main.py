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

from modeling.dcf import historical_DCF, enhanced_DCF_with_trends
from visualization.plot import visualize_bulk_historicals
from visualization.printouts import prettyprint
# Logging setup
from logging_config import get_logger, log_progress

logger = get_logger(__name__)



def main(args):
    """
    Run DCF analysis with trend analysis and comprehensive output.
    Uses enhanced DCF with fmpsdk data access and dynamic growth rates.
    """
    import json
    
    ticker = args.t
    logger.info(f"Starting DCF analysis for {ticker}")

    if args.s > 0:
        # Sensitivity analysis mode
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
                valid_variables = ['earnings_growth_rate', 'eg', 'cap_ex_growth_rate', 'cg', 
                                 'perpetual_growth_rate', 'pg', 'discount_rate', 'discount']
                raise ValueError(f'Invalid variable "{args.v}". Valid options: {valid_variables}')
        else:
            raise ValueError('If step (-- s) is > 0, you must specify the variable via --v.')
            
        # Use visualization for sensitivity analysis
        if args.y > 1:
            visualize_bulk_historicals(dcfs, ticker, cond, args.apikey)
        else:
            prettyprint(dcfs, args.y)
    else:
        # Standard DCF analysis with trend analysis
        try:
            result = enhanced_DCF_with_trends(
                ticker=ticker,
                years_back=args.years_back,
                forecast_years=args.p,
                discount_rate=args.d if args.d != 0.1 else None,  # Use dynamic WACC if default
                perpetual_growth_rate=args.pg,
                apikey=args.apikey
            )
            
            if 'error' in result:
                logger.error(f"Analysis failed: {result['error']}")
                return
            
            # Display results
            _display_results(result)
            
            # Save to JSON if requested
            if args.output_json:
                with open(args.output_json, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                logger.info(f"Results saved to {args.output_json}")
                
        except Exception as e:
            logger.error(f"DCF analysis failed: {e}")
            raise


def _display_results(result: dict):
    """Display DCF analysis results using structured logging"""
    ticker = result['ticker']
    dcf_val = result.get('dcf_valuation', {})
    trends = result.get('trend_analysis', {})
    enhanced = result.get('enhanced_metrics', {})
    
    logger.info("="*80)
    logger.info(f"DCF ANALYSIS RESULTS FOR {ticker}")
    logger.info("="*80)
    
    # Key Valuation Results
    logger.info("📊 VALUATION SUMMARY:")
    logger.info(f"   • Intrinsic Value per Share: ${enhanced.get('intrinsic_value', 0):.2f}")
    logger.info(f"   • Enterprise Value: ${enhanced.get('enterprise_value', 0):,.0f}")
    logger.info(f"   • Equity Value: ${enhanced.get('equity_value', 0):,.0f}")
    
    # Growth Analysis
    logger.info("📈 GROWTH ANALYSIS:")
    logger.info(f"   • Revenue CAGR: {enhanced.get('revenue_cagr', 0):.1%}")
    logger.info(f"   • EBITDA CAGR: {enhanced.get('ebitda_cagr', 0):.1%}")
    logger.info(f"   • FCFE CAGR: {enhanced.get('fcfe_cagr', 0):.1%}")
    
    # DCF Details  
    logger.info("💰 DCF PARAMETERS:")
    logger.info(f"   • Discount Rate (WACC): {result.get('discount_rate', 0):.1%}")
    logger.info(f"   • Terminal Growth Rate: {result.get('terminal_growth_rate', 0):.1%}")
    logger.info(f"   • Years Analyzed: {result.get('years_analyzed', 0)}")
    logger.info(f"   • Forecast Years: {result.get('forecast_years', 0)}")
    
    # Data Source
    logger.info("📋 DATA:")
    logger.info(f"   • Source: {result.get('data_source', 'N/A')}")
    logger.info(f"   • Analysis Date: {result.get('analysis_date', 'N/A')}")
    
    logger.info("="*80)
    logger.info("Analysis complete!")
    logger.info("="*80)


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
    
    # Analysis options
    parser.add_argument('--years_back', type=int, default=10, help='Years of historical data for trend analysis')
    parser.add_argument('--output_json', help='Save results to JSON file')

    args = parser.parse_args()
    main(args)
