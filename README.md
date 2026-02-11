# Portfolio_Tracker
Robo-Advisor Portfolio Management System
A comprehensive portfolio tracking and optimization platform with German tax compliance, broker integrations, and risk analytics.

Features
Portfolio Management
Transaction tracking (Buy/Sell)
Holdings calculation with average cost basis
Realized P&L calculation (FIFO method)
Unrealized P&L tracking
Broker Integrations
Trading212 - API sync & PDF/CSV import
Binance - Full trade history sync
Portfolio Optimization
Maximum Sharpe Ratio optimization
Minimum Volatility optimization
Target Return optimization
Discrete share allocation
Risk Analytics
Volatility (annualized)
Sharpe Ratio
Maximum Drawdown
Beta calculation
Correlation Matrix
Monte Carlo Simulation
German Tax Compliance
Sparerpauschbetrag tracking (€1,000 single / €2,000 married)
Abgeltungsteuer calculation (25%)
Solidaritätszuschlag (5.5%)
Kirchensteuer support (8-9%)
Tax-loss harvesting insights
Tech Stack
Backend: Python, FastAPI
Database: SQLAlchemy ORM
APIs: Alpha Vantage, Trading212, Binance
Optimization: PyPortfolioOpt
Data Processing: Pandas, NumPy
Installation
# Clone repository
git clone https://github.com/cihatozkurt/robo-advisor.git
cd robo-advisor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys
Configuration
Create a .env file:

# Alpha Vantage (for price data)
ALPHA_VANTAGE_API_KEY=your_key_here

# Trading212 (optional)
TRADING212_API_KEY=your_api_key
TRADING212_API_KEY_ID=your_key_id

# Binance (optional)
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key
Project Structure
app/
├── services/
│   ├── portfolio_service.py    # Portfolio & transaction management
│   ├── price_service.py        # Real-time price data
│   ├── risk_service.py         # Risk metrics & analytics
│   ├── optimization_service.py # Portfolio optimization
│   ├── tax_service.py          # German tax calculations
│   ├── trading212_service.py   # Trading212 integration
│   ├── binance_service.py      # Binance integration
│   ├── broker_service.py       # PDF/CSV import
│   └── user_service.py         # Authentication
├── database/
│   └── models.py               # SQLAlchemy models
└── config.py                   # Configuration
Usage Examples
Portfolio Optimization
from app.services.optimization_service import OptimizationService

optimizer = OptimizationService()
result, error = optimizer.optimize_max_sharpe(
    symbols=["AAPL", "MSFT", "GOOGL", "AMZN"],
    risk_free_rate=0.05
)
print(result["weights"])
print(f"Expected Return: {result['expected_return']:.2%}")
print(f"Sharpe Ratio: {result['sharpe_ratio']:.2f}")
Tax Calculation
from app.services.tax_service import TaxService

tax_service = TaxService(user)
tax_result = tax_service.calculate_tax_on_gains(realized_gains=5000)
print(f"Tax-free amount: €{tax_result['tax_free_amount']}")
print(f"Total tax: €{tax_result['total_tax']:.2f}")
print(f"Net gains: €{tax_result['net_gains']:.2f}")
Risk Analysis
from app.services.risk_service import RiskService

risk_service = RiskService()
metrics = risk_service.get_portfolio_risk_metrics(
    symbols=["AAPL", "MSFT"],
    weights=[0.6, 0.4]
)
print(f"Portfolio Volatility: {metrics['portfolio']['volatility']:.2%}")
print(f"Sharpe Ratio: {metrics['portfolio']['sharpe_ratio']:.2f}")
API Endpoints
Endpoint	Method	Description
/api/portfolio	GET	Get portfolio summary
/api/transactions	POST	Add transaction
/api/sync/trading212	POST	Sync Trading212
/api/sync/binance	POST	Sync Binance
/api/optimize	POST	Optimize portfolio
/api/risk	GET	Get risk metrics
/api/tax	GET	Get tax summary
