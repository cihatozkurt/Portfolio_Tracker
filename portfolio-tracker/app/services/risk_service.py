import numpy as np
import pandas as pd
from alpha_vantage.timeseries import TimeSeries
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import Config

class RiskService:
    def __init__(self):
        self.ts = TimeSeries(key=Config.ALPHA_VANTAGE_API_KEY, output_format='pandas')
    
    def get_historical_prices(self, symbol: str, period: str = "full"):
        """Get historical daily prices for a symbol"""
        try:
            data, meta = self.ts.get_daily(symbol=symbol, outputsize='compact')
            data = data.sort_index()
            return data['4. close']
        except Exception as e:
            return None
    
    def calculate_returns(self, prices: pd.Series):
        """Calculate daily returns"""
        return prices.pct_change().dropna()
    
    def calculate_volatility(self, returns: pd.Series, annualize: bool = True):
        """Calculate volatility (standard deviation of returns)"""
        vol = returns.std()
        if annualize:
            vol = vol * np.sqrt(252)
        return vol
    
    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.05):
        """Calculate Sharpe Ratio"""
        excess_returns = returns.mean() * 252 - risk_free_rate
        volatility = self.calculate_volatility(returns)
        if volatility == 0:
            return 0
        return excess_returns / volatility
    
    def calculate_max_drawdown(self, prices: pd.Series):
        """Calculate Maximum Drawdown"""
        cumulative = (1 + prices.pct_change()).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def calculate_beta(self, stock_returns: pd.Series, market_returns: pd.Series):
        """Calculate Beta relative to market"""
        covariance = stock_returns.cov(market_returns)
        market_variance = market_returns.var()
        if market_variance == 0:
            return 0
        return covariance / market_variance
    
    def get_portfolio_risk_metrics(self, symbols: list, weights: list = None):
        """Calculate risk metrics for entire portfolio"""
        if weights is None:
            weights = [1/len(symbols)] * len(symbols)
        
        all_returns = {}
        metrics = {}
        
        for symbol in symbols:
            prices = self.get_historical_prices(symbol)
            if prices is not None and len(prices) > 0:
                all_returns[symbol] = self.calculate_returns(prices)
                
                metrics[symbol] = {
                    "volatility": self.calculate_volatility(all_returns[symbol]),
                    "sharpe_ratio": self.calculate_sharpe_ratio(all_returns[symbol]),
                    "max_drawdown": self.calculate_max_drawdown(prices)
                }
        
        if all_returns:
            returns_df = pd.DataFrame(all_returns).dropna()
            
            if not returns_df.empty:
                portfolio_returns = (returns_df * weights[:len(returns_df.columns)]).sum(axis=1)
                
                metrics["portfolio"] = {
                    "volatility": self.calculate_volatility(portfolio_returns),
                    "sharpe_ratio": self.calculate_sharpe_ratio(portfolio_returns),
                    "max_drawdown": self.calculate_max_drawdown((1 + portfolio_returns).cumprod())
                }
        
        return metrics
    
    def get_cumulative_returns(self, symbols: list):
        """Get cumulative returns for charting"""
        all_data = {}
        
        for symbol in symbols:
            prices = self.get_historical_prices(symbol)
            if prices is not None and len(prices) > 0:
                returns = self.calculate_returns(prices)
                cumulative = (1 + returns).cumprod() - 1
                all_data[symbol] = cumulative * 100  # Convert to percentage
        
        if all_data:
            return pd.DataFrame(all_data)
        return None
    
    def get_correlation_matrix(self, symbols: list):
        """Get correlation matrix between symbols"""
        all_returns = {}
        
        for symbol in symbols:
            prices = self.get_historical_prices(symbol)
            if prices is not None and len(prices) > 0:
                all_returns[symbol] = self.calculate_returns(prices)
        
        if all_returns:
            returns_df = pd.DataFrame(all_returns).dropna()
            return returns_df.corr()
        return None
    
    def monte_carlo_simulation(self, current_value: float, annual_return: float = 0.08, 
                                volatility: float = 0.15, years: int = 10, 
                                simulations: int = 1000):
        """Run Monte Carlo simulation for portfolio growth"""
        days = years * 252
        daily_return = annual_return / 252
        daily_vol = volatility / np.sqrt(252)
        
        results = np.zeros((simulations, days))
        
        for i in range(simulations):
            prices = [current_value]
            for _ in range(days - 1):
                shock = np.random.normal(daily_return, daily_vol)
                prices.append(prices[-1] * (1 + shock))
            results[i] = prices
        
        return results