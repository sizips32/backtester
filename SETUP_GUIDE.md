# Portfolio BackTester - Claude Desktop Setup Guide

## Current Status
✅ **Claude Desktop Configuration**: Completed
⚠️ **MCP Library Issue**: Python/Pydantic compatibility issue
✅ **Core Portfolio Analysis**: Fully functional
✅ **Streamlit Interface**: Working

## Quick Setup for Claude Desktop

### 1. Configuration File Created
Your Claude Desktop is configured at:
```
~/.config/claude-desktop/claude_desktop_config.json
```

### 2. Manual MCP Testing (Recommended)

Since there's a temporary MCP library compatibility issue, here are alternative ways to use the portfolio analysis system:

#### Option A: Direct Python Usage
```bash
cd /Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester

# Run the Streamlit interface
streamlit run main.py

# Or use components directly
python -c "
from components.backtesting import PortfolioBacktest
from utils.data_service import DataService

# Example usage
data_service = DataService()
backtester = PortfolioBacktest(data_service)

# Test with sample portfolio
assets = ['AAPL', 'GOOGL', 'MSFT']
weights = [0.4, 0.3, 0.3]
start_date = '2023-01-01'
end_date = '2023-12-31'

result = backtester.run_comprehensive_backtest(assets, weights, start_date, end_date)
print('Portfolio Return:', result['portfolio_metrics']['total_return'])
"
```

#### Option B: Test Individual Analysis Tools
```bash
# Test portfolio optimization
python -c "
import sys
sys.path.append('/Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester')

from mcp_tools import PortfolioAnalysisTools
import asyncio

async def test_optimization():
    tools = PortfolioAnalysisTools()
    result = await tools._optimize_portfolio({
        'assets': ['AAPL', 'GOOGL', 'MSFT', 'TSLA'],
        'objective': 'max_sharpe',
        'constraints': {'max_weight': 0.4, 'min_weight': 0.05},
        'lookback_period': 252
    })
    print('Optimization Result:', result)

asyncio.run(test_optimization())
"
```

### 3. Available Analysis Features

Even without MCP, you can access all portfolio analysis features:

#### Core Features:
- ✅ Portfolio backtesting with performance metrics
- ✅ Risk analysis (VaR, CVaR, volatility)
- ✅ Portfolio optimization (max Sharpe, min volatility)
- ✅ Monte Carlo simulation
- ✅ Stress testing
- ✅ Correlation analysis
- ✅ Performance attribution

#### Advanced Features:
- ✅ Multi-asset portfolio construction
- ✅ Benchmark comparison
- ✅ Historical data analysis
- ✅ Risk-adjusted returns
- ✅ Drawdown analysis

### 4. Troubleshooting MCP Issues

If you want to resolve the MCP compatibility issue:

```bash
# Try creating a virtual environment
python -m venv portfolio_mcp_env
source portfolio_mcp_env/bin/activate  # On macOS/Linux
# portfolio_mcp_env\Scripts\activate  # On Windows

# Install compatible versions
pip install "pydantic>=2.0.0,<2.11.0"
pip install "mcp>=0.9.1,<1.0.0"
pip install pandas numpy scipy yfinance streamlit plotly psutil
```

### 5. Using the Streamlit Interface

The full portfolio analysis system is available through the web interface:

```bash
cd /Users/soonjaekim/Desktop/SGR/SAMANDA_FE/BackTester
streamlit run main.py
```

This provides:
- Interactive portfolio builder
- Real-time performance analysis
- Risk assessment tools
- Optimization algorithms
- Historical backtesting
- Advanced analytics

### 6. Example Analysis Workflow

```python
# 1. Create a portfolio
assets = ['AAPL', 'GOOGL', 'MSFT']
weights = [0.4, 0.3, 0.3]

# 2. Run backtest
backtest_result = backtester.run_comprehensive_backtest(
    assets=assets,
    weights=weights,
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# 3. Analyze risk
risk_metrics = risk_analyzer.calculate_portfolio_risk(
    assets=assets,
    weights=weights,
    confidence_level=0.95
)

# 4. Optimize portfolio
optimal_weights = optimizer.optimize_portfolio(
    assets=['AAPL', 'GOOGL', 'MSFT', 'TSLA'],
    objective='max_sharpe'
)
```

## Next Steps

1. **Immediate Use**: Start with the Streamlit interface (`streamlit run main.py`)
2. **MCP Resolution**: Work on resolving the Python environment compatibility
3. **Claude Integration**: Once MCP works, Claude Desktop will automatically detect the server

## Support

- All core functionality works independently of MCP
- The portfolio analysis system is production-ready
- MCP integration will enhance AI agent capabilities but isn't required for analysis

Your Portfolio BackTester is fully functional and ready to use!