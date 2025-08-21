# DCF Submodule - Technical Documentation

## Overview

This document provides comprehensive technical documentation for the DCF (Discounted Cash Flow) submodule, addressing the technical debt that previously included 10+ TODO comments and hardcoded magic numbers.

## Key Improvements Made

### 1. Configuration Management
**Problem**: Hardcoded values like `return .1` and `cwc * 0.7` without documentation
**Solution**: Moved all parameters to `config.yaml` under `forecasting.dcf` section

### 2. WACC Calculation
**Problem**: `return .1` hardcoded placeholder
**Solution**: Implemented proper CAPM-based WACC calculation with industry defaults

### 3. Working Capital Modeling
**Problem**: Unexplained `cwc * 0.7` decay rate
**Solution**: Made configurable with clear documentation of working capital decay assumption

## DCF Model Architecture

### Core Formula
The DCF model implements the standard enterprise value calculation:

```
Enterprise Value = NPV(Explicit FCF) + NPV(Terminal Value)
Equity Value = Enterprise Value - Net Debt + Cash
Share Price = Equity Value / Shares Outstanding
```

### Free Cash Flow Calculation
```
Unlevered FCF = EBIT × (1 - Tax Rate) + Depreciation + ΔCWC + CapEx
```

Where:
- `EBIT`: Earnings Before Interest and Taxes
- `Tax Rate`: Corporate tax rate (bounded between 15%-35%)
- `Depreciation`: Non-cash charges (D&A)
- `ΔCWC`: Change in Working Capital (with decay factor)
- `CapEx`: Capital Expenditures

### Variable Growth Rate Support

The model supports three growth rate input formats:

1. **Constant Growth**: Single rate applied to all forecast periods
2. **Dictionary Format**: Year-specific growth rates
   ```python
   {2025: -0.076, 2026: 0.305, 2027: 0.059, ...}
   ```
3. **List Format**: Sequential growth rates
   ```python
   [-0.076, 0.305, 0.059, 0.049, 0.050, ...]
   ```

### Terminal Value Calculation

Uses Gordon Growth Model:
```
Terminal Value = Final FCF × (1 + g) / (WACC - g)
```

Where `g` is bounded between 2%-4% for realistic perpetual growth assumptions.

## Configuration Parameters

### Default Rates (config.yaml)
```yaml
dcf:
  default_discount_rate: 0.10          # 10% WACC default
  default_earnings_growth_rate: 0.05   # 5% earnings growth
  default_capex_growth_rate: 0.045     # 4.5% capex growth
  working_capital_decay_rate: 0.7      # CWC decay factor
```

### WACC Components
```yaml
dcf:
  risk_free_rate: 0.04          # 10-year Treasury rate
  market_premium: 0.06          # Equity risk premium
  small_company_premium: 0.03   # Small cap premium
```

### Industry Beta Defaults
```yaml
beta_defaults:
  technology: 1.3
  healthcare: 1.1
  financials: 1.2
  utilities: 0.8
  energy: 1.4
  default: 1.0
```

### Data Validation Thresholds
```yaml
dcf:
  max_forecast_periods: 15
  min_forecast_periods: 3
  ebitda_margin_sanity_check: 0.50     # Flag >50% margins
  revenue_growth_sanity_check: 2.0     # Flag >200% growth
```

## WACC Calculation Method

### Enhanced get_discount_rate() Function

The improved WACC calculation follows this hierarchy:

1. **Full WACC** (when all data available):
   ```
   WACC = (E/V × Cost of Equity) + (D/V × Cost of Debt × (1 - Tax Rate))
   ```

2. **Cost of Equity Only** (when capital structure unavailable):
   ```
   Cost of Equity = Risk-Free Rate + Beta × Market Premium
   ```

3. **Industry Default** (when company beta unavailable):
   Uses industry-specific beta from configuration

### Cost of Debt Estimation
```python
debt_spread = min(0.05, debt_to_equity * 0.02)  # Max 5% spread
cost_of_debt = risk_free_rate + debt_spread
```

## Working Capital Modeling

### Decay Rate Rationale
The `working_capital_decay_rate: 0.7` represents the assumption that working capital changes moderate over time as companies optimize their cash conversion cycles.

**Economic Logic**:
- Year 1: Full working capital impact
- Year 2+: 70% of previous year's working capital change
- Models realistic business cycle normalization

### Formula Application
```python
cwc = cwc * DCF_CONFIG.working_capital_decay_rate
```

This replaces the previous unexplained `cwc * 0.7` with a configurable, documented parameter.

## Data Validation and Error Handling

### Input Validation
1. **Forecast Period Bounds**: 3-15 years
2. **Growth Rate Sanity Checks**: Flag extreme values
3. **Tax Rate Bounds**: 15%-35% range
4. **Terminal Growth Limits**: 2%-4% maximum

### Error Recovery
1. **Missing EBIT**: Prompts for manual input
2. **Invalid Financial Data**: Graceful degradation
3. **API Failures**: Logged with detailed error messages

## Performance Optimizations

### Memory Efficiency
- Iterative FCF calculation (no large array storage)
- Configurable forecast horizons
- Lazy loading of configuration

### Logging Integration
- Debug-level calculation details
- Info-level summary results
- Warning-level data quality issues
- Error-level calculation failures

## API and Usage

### Single Company DCF
```python
dcf_result = DCF(
    ticker="AAPL",
    ev_statement=ev_data,
    income_statement=income_data,
    balance_statement=balance_data,
    cashflow_statement=cashflow_data,
    discount_rate=0.10,
    forecast=10,
    earnings_growth_rate=0.05,
    cap_ex_growth_rate=0.045,
    perpetual_growth_rate=0.025
)
```

### Variable Growth DCF
```python
variable_rates = {
    2025: -0.076,  # Decline phase
    2026: 0.305,   # Recovery phase
    2027: 0.059,   # Normalization
    2028: 0.049,   # Steady state
    2029: 0.050    # Long-term
}

dcf_result = DCF(
    ticker="PLTR",
    # ... other parameters ...
    variable_growth_rates=variable_rates
)
```

### Batch Processing
```python
results = multiple_tickers(
    tickers=["AAPL", "MSFT", "GOOGL"],
    years=5,
    forecast_periods=10,
    discount_rate=0.10,
    earnings_growth_rate=0.05,
    cap_ex_growth_rate=0.045,
    perpetual_growth_rate=0.025
)
```

## Return Format

```python
{
    'date': '2023-12-31',           # Statement date
    'enterprise_value': 2500000000, # Total enterprise value
    'equity_value': 2200000000,     # Equity value after debt adjustment
    'share_price': 157.50          # Per-share intrinsic value
}
```

## Integration with Stock Discovery Pipeline

### Configuration Integration
The DCF module integrates with the main pipeline configuration system through:
```python
from config_manager import get_config
config = get_config()
DCF_CONFIG = config.forecasting.dcf
```

### Logging Integration
Uses the centralized logging system:
```python
logger = logging.getLogger(__name__)
logger.info(f"DCF Results for {ticker}: Share Price: ${share_price:.2E}")
```

### Error Handling Integration
Follows the pipeline's error handling patterns with graceful degradation and detailed logging.

## Testing Considerations

### Unit Tests Needed
1. **WACC Calculation**: Test with various capital structures
2. **Growth Rate Processing**: Test dict/list/constant formats
3. **Terminal Value**: Test bounds and calculation accuracy
4. **Configuration Loading**: Test fallback behavior

### Integration Tests Needed
1. **Full DCF Workflow**: End-to-end calculation
2. **Batch Processing**: Multiple ticker handling
3. **Error Scenarios**: Missing data handling
4. **Performance**: Large dataset processing

## Migration Notes

### Breaking Changes
1. `get_discount_rate()` now accepts parameters (backward compatible with defaults)
2. Configuration file required for full functionality
3. Enhanced error reporting may surface previously silent issues

### Backward Compatibility
- All existing function signatures maintained
- Default values preserve original behavior
- Configuration system provides fallbacks

## Future Enhancements

### Potential Improvements
1. **Monte Carlo Simulation**: Risk-adjusted valuations
2. **Sensitivity Analysis**: Automated parameter sweeps
3. **Real Options Valuation**: Growth option modeling
4. **ESG Integration**: Sustainability risk adjustments

### Technical Debt Eliminated
- ✅ Removed all TODO comments with proper implementations
- ✅ Eliminated hardcoded magic numbers
- ✅ Added comprehensive documentation
- ✅ Implemented proper WACC calculation
- ✅ Created configurable parameter system
- ✅ Enhanced error handling and validation

This documentation addresses all the technical debt issues identified in the original assessment, providing a production-ready DCF calculation engine with proper configuration management, error handling, and documentation.