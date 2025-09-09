import os
import json
import fmpsdk
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date
from decimal import Decimal
from dotenv import load_dotenv
from box import Box, BoxList

# Load environment variables
load_dotenv()

class FMPClient:
    """Enhanced client for Financial Modeling Prep API using fmpsdk"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()
        
    def _get_api_key(self) -> str:
        """Get FMP API key from environment"""
        api_key = os.getenv('FINANCIAL_MODELING_PREP_KEY') or os.getenv('FMP_API_KEY')
        if not api_key:
            raise ValueError("FMP API key not found. Set FINANCIAL_MODELING_PREP_KEY or FMP_API_KEY environment variable")
        return api_key
    
    def _to_box(self, data: List[Dict[str, Any]]) -> BoxList:
        """Convert FMP response to Box objects for cleaner access"""
        return BoxList([Box(item, default_box=True, default_box_attr=None) for item in data])
    
    def get_income_statement(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict[str, Any]]:
        """Get income statements for a ticker"""
        return fmpsdk.income_statement(
            apikey=self.api_key,
            symbol=ticker.upper(),
            period=period,
            limit=limit
        )
    
    def get_income_statement_box(self, ticker: str, period: str = "annual", limit: int = 10) -> BoxList:
        """Get income statements for a ticker as Box objects"""
        data = self.get_income_statement(ticker, period, limit)
        return self._to_box(data)
    
    def get_balance_sheet(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict[str, Any]]:
        """Get balance sheet statements for a ticker"""
        return fmpsdk.balance_sheet_statement(
            apikey=self.api_key,
            symbol=ticker.upper(),
            period=period,
            limit=limit
        )
    
    def get_cash_flow_statement(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict[str, Any]]:
        """Get cash flow statements for a ticker"""
        return fmpsdk.cash_flow_statement(
            apikey=self.api_key,
            symbol=ticker.upper(),
            period=period,
            limit=limit
        )
    
    def get_company_profile(self, ticker: str) -> List[Dict[str, Any]]:
        """Get company profile information"""
        return fmpsdk.company_profile(
            apikey=self.api_key,
            symbol=ticker.upper()
        )
    
    def get_key_metrics(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict[str, Any]]:
        """Get key financial metrics"""
        return fmpsdk.key_metrics(
            apikey=self.api_key,
            symbol=ticker.upper(),
            period=period,
            limit=limit
        )
    
    def get_financial_ratios(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict[str, Any]]:
        """Get financial ratios"""
        return fmpsdk.financial_ratios(
            apikey=self.api_key,
            symbol=ticker.upper(),
            period=period,
            limit=limit
        )
    
    def get_enterprise_values(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict[str, Any]]:
        """Get enterprise values"""
        return fmpsdk.enterprise_values(
            apikey=self.api_key,
            symbol=ticker.upper(),
            period=period,
            limit=limit
        )
    
    def get_dcf_values(self, ticker: str) -> List[Dict[str, Any]]:
        """Get DCF valuation"""
        return fmpsdk.discounted_cash_flow(
            apikey=self.api_key,
            symbol=ticker.upper()
        )
    
    def get_financial_growth(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict[str, Any]]:
        """Get financial growth metrics"""
        return fmpsdk.financial_growth(
            apikey=self.api_key,
            symbol=ticker.upper(),
            period=period,
            limit=limit
        )
    
    def get_income_statement_growth(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict[str, Any]]:
        """Get income statement growth rates"""
        return fmpsdk.income_statement_growth(
            apikey=self.api_key,
            symbol=ticker.upper(),
            period=period,
            limit=limit
        )
    
    def get_balance_sheet_growth(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict[str, Any]]:
        """Get balance sheet growth rates"""
        return fmpsdk.balance_sheet_statement_growth(
            apikey=self.api_key,
            symbol=ticker.upper(),
            period=period,
            limit=limit
        )
    
    def get_cash_flow_growth(self, ticker: str, period: str = "annual", limit: int = 10) -> List[Dict[str, Any]]:
        """Get cash flow growth rates"""
        return fmpsdk.cash_flow_statement_growth(
            apikey=self.api_key,
            symbol=ticker.upper(),
            period=period,
            limit=limit
        )
        
    def get_quote(self, ticker: str) -> List[Dict[str, Any]]:
        """Get real-time quote"""
        return fmpsdk.quote(
            apikey=self.api_key,
            symbol=ticker.upper()
        )
    
    def get_market_cap(self, ticker: str) -> List[Dict[str, Any]]:
        """Get market capitalization"""
        return fmpsdk.market_capitalization(
            apikey=self.api_key,
            symbol=ticker.upper()
        )
    
    def get_all_financial_data(self, ticker: str, period: str = "annual", limit: int = 10) -> Dict[str, Any]:
        """Get comprehensive financial data for a ticker using fmpsdk"""
        ticker = ticker.upper()
        
        try:
            # Core financial statements
            income_statements = self.get_income_statement(ticker, period, limit)
            balance_sheets = self.get_balance_sheet(ticker, period, limit)
            cash_flows = self.get_cash_flow_statement(ticker, period, limit)
            
            # Company information
            company_profile = self.get_company_profile(ticker)
            
            # Financial metrics and ratios
            key_metrics = self.get_key_metrics(ticker, period, limit)
            financial_ratios = self.get_financial_ratios(ticker, period, limit)
            enterprise_values = self.get_enterprise_values(ticker, period, limit)
            
            # Growth data
            financial_growth = self.get_financial_growth(ticker, period, limit)
            income_growth = self.get_income_statement_growth(ticker, period, limit)
            balance_growth = self.get_balance_sheet_growth(ticker, period, limit)
            cashflow_growth = self.get_cash_flow_growth(ticker, period, limit)
            
            # Valuation
            dcf_values = self.get_dcf_values(ticker)
            
            # Market data
            quote = self.get_quote(ticker)
            market_cap = self.get_market_cap(ticker)
            
            return {
                "ticker": ticker,
                "period": period,
                "limit": limit,
                "retrieved_at": datetime.now().isoformat(),
                "data_source": "fmpsdk",
                "data": {
                    # Core financial statements
                    "income_statements": income_statements,
                    "balance_sheets": balance_sheets,
                    "cash_flow_statements": cash_flows,
                    
                    # Company information
                    "company_profile": company_profile,
                    
                    # Metrics and ratios
                    "key_metrics": key_metrics,
                    "financial_ratios": financial_ratios,
                    "enterprise_values": enterprise_values,
                    
                    # Growth data
                    "financial_growth": financial_growth,
                    "income_statement_growth": income_growth,
                    "balance_sheet_growth": balance_growth,
                    "cash_flow_growth": cashflow_growth,
                    
                    # Valuation
                    "dcf_values": dcf_values,
                    
                    # Market data
                    "quote": quote,
                    "market_capitalization": market_cap
                }
            }
            
        except Exception as e:
            return {
                "ticker": ticker,
                "period": period,
                "limit": limit,
                "retrieved_at": datetime.now().isoformat(),
                "error": str(e),
                "data": {}
            }
    
    def save_to_json(self, data: Dict[str, Any], filename: str) -> None:
        """Save data to JSON file"""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Custom JSON encoder for Decimal and datetime objects
        def json_encoder(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, (datetime, date)):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=json_encoder)
            
    def fetch_and_save_historical_data(self, ticker: str, output_dir: str = "temp_data") -> str:
        """Fetch all historical data and save to JSON file"""
        ticker = ticker.upper()
        
        # Get comprehensive financial data
        data = self.get_all_financial_data(ticker, period="annual", limit=20)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/{ticker}_historical_{timestamp}.json"
        self.save_to_json(data, filename)
        
        return filename
    
    def get_data_matching_report_columns(self, ticker: str, report_date: Optional[date] = None, years_back: int = 10) -> Dict[str, Any]:
        """
        Get data specifically matching the columns shown in UNH.jpeg report:
        - Revenue, CAPEX, Debt, FCFE, Shares, FCF/Share, Price Estimate, FCFE Yield
        - EBITDA, Debt, EBITDA/Debt, Net Cash, EV, EV/EBITDA, ROA/EBITDA
        """
        ticker = ticker.upper()
        limit = years_back
        
        try:
            # Get all required data
            income_statements = self.get_income_statement(ticker, "annual", limit)
            balance_sheets = self.get_balance_sheet(ticker, "annual", limit)
            cash_flows = self.get_cash_flow_statement(ticker, "annual", limit)
            key_metrics = self.get_key_metrics(ticker, "annual", limit)
            financial_ratios = self.get_financial_ratios(ticker, "annual", limit)
            enterprise_values = self.get_enterprise_values(ticker, "annual", limit)
            company_profile = self.get_company_profile(ticker)
            financial_growth = self.get_financial_growth(ticker, "annual", limit)
            
            # Process data to match report columns
            processed_data = {
                "ticker": ticker,
                "report_date": report_date.isoformat() if report_date else date.today().isoformat(),
                "retrieved_at": datetime.now().isoformat(),
                "years_requested": years_back,
                "raw_data": {
                    "income_statements": income_statements,
                    "balance_sheets": balance_sheets,
                    "cash_flow_statements": cash_flows,
                    "key_metrics": key_metrics,
                    "financial_ratios": financial_ratios,
                    "enterprise_values": enterprise_values,
                    "company_profile": company_profile,
                    "financial_growth": financial_growth
                },
                "report_columns": self._extract_report_columns(
                    income_statements, balance_sheets, cash_flows,
                    key_metrics, financial_ratios, enterprise_values
                )
            }
            
            return processed_data
            
        except Exception as e:
            return {
                "ticker": ticker,
                "error": str(e),
                "retrieved_at": datetime.now().isoformat()
            }
    
    def _extract_report_columns(self, income_statements, balance_sheets, cash_flows, 
                              key_metrics, financial_ratios, enterprise_values) -> Dict[str, List[Dict]]:
        """Extract specific columns matching the reference reports"""
        
        # Combine data by year
        years_data = {}
        
        # Process each year from income statements
        for stmt in income_statements:
            year = stmt.get('calendarYear')
            if not year:
                continue
                
            if year not in years_data:
                years_data[year] = {
                    'year': year,
                    'date': stmt.get('date'),
                    'period': stmt.get('period')
                }
            
            # Extract revenue, EBITDA calculations
            years_data[year].update({
                'revenue': stmt.get('revenue'),
                'operating_income': stmt.get('operatingIncome'),
                'depreciation_amortization': stmt.get('depreciationAndAmortization', 0),
                'shares_outstanding': stmt.get('weightedAverageShsOut'),
                'eps': stmt.get('eps')
            })
            
            # Calculate EBITDA
            if stmt.get('operatingIncome') and stmt.get('depreciationAndAmortization'):
                years_data[year]['ebitda'] = stmt.get('operatingIncome') + stmt.get('depreciationAndAmortization')
        
        # Add balance sheet data
        for stmt in balance_sheets:
            year = stmt.get('calendarYear')
            if year in years_data:
                years_data[year].update({
                    'total_debt': stmt.get('totalDebt'),
                    'cash_and_equivalents': stmt.get('cashAndCashEquivalents'),
                    'total_assets': stmt.get('totalAssets'),
                    'shareholders_equity': stmt.get('totalStockholdersEquity')
                })
                
                # Calculate net cash
                if stmt.get('cashAndCashEquivalents') and stmt.get('totalDebt'):
                    years_data[year]['net_cash'] = stmt.get('cashAndCashEquivalents') - stmt.get('totalDebt')
        
        # Add cash flow data
        for stmt in cash_flows:
            year = stmt.get('calendarYear')
            if year in years_data:
                years_data[year].update({
                    'operating_cash_flow': stmt.get('operatingCashFlow'),
                    'capital_expenditures': stmt.get('capitalExpenditure', 0),
                    'free_cash_flow': stmt.get('freeCashFlow'),
                    'dividends_paid': stmt.get('dividendsPaid')
                })
                
                # Calculate FCFE (Free Cash Flow to Equity)
                if stmt.get('freeCashFlow') and stmt.get('dividendsPaid'):
                    years_data[year]['fcfe'] = stmt.get('freeCashFlow') - abs(stmt.get('dividendsPaid', 0))
                elif stmt.get('freeCashFlow'):
                    years_data[year]['fcfe'] = stmt.get('freeCashFlow')
        
        # Add key metrics
        for metrics in key_metrics:
            year = metrics.get('calendarYear')
            if year in years_data:
                years_data[year].update({
                    'market_cap': metrics.get('marketCap'),
                    'enterprise_value': metrics.get('enterpriseValue'),
                    'pe_ratio': metrics.get('peRatio'),
                    'ev_to_revenue': metrics.get('evToRevenue'),
                    'ev_to_ebitda': metrics.get('enterpriseValueOverEBITDA'),
                    'price_per_share': metrics.get('stockPrice')
                })
        
        # Add financial ratios
        for ratios in financial_ratios:
            year = ratios.get('calendarYear')
            if year in years_data:
                years_data[year].update({
                    'debt_to_equity': ratios.get('debtEquityRatio'),
                    'return_on_assets': ratios.get('returnOnAssets'),
                    'return_on_equity': ratios.get('returnOnEquity'),
                    'current_ratio': ratios.get('currentRatio')
                })
        
        # Calculate additional metrics
        for year, data in years_data.items():
            # FCF per share
            if data.get('free_cash_flow') and data.get('shares_outstanding'):
                data['fcf_per_share'] = data['free_cash_flow'] / data['shares_outstanding']
            
            # FCFE Yield
            if data.get('fcfe') and data.get('market_cap'):
                data['fcfe_yield'] = data['fcfe'] / data['market_cap']
            
            # EBITDA to Debt ratio
            if data.get('ebitda') and data.get('total_debt') and data['total_debt'] > 0:
                data['ebitda_debt_ratio'] = data['ebitda'] / data['total_debt']
            
            # ROA/EBITDA (unusual ratio, but matching report)
            if data.get('return_on_assets') and data.get('ebitda') and data.get('total_assets'):
                ebitda_margin = data['ebitda'] / data.get('revenue', 1) if data.get('revenue') else 0
                data['roa_ebitda_ratio'] = data.get('return_on_assets', 0) / ebitda_margin if ebitda_margin else 0
        
        return {
            "yearly_data": list(years_data.values()),
            "available_years": sorted(years_data.keys(), reverse=True),
            "data_points": len(years_data)
        }