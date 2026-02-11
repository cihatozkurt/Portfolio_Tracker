import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier, risk_models, expected_returns
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.services.risk_service import RiskService

class OptimizationService:
    def __init__(self):
        self.risk_service = RiskService()
    
    def get_price_data(self, symbols: list):
        """Get historical price data for multiple symbols"""
        all_prices = {}
        
        for symbol in symbols:
            prices = self.risk_service.get_historical_prices(symbol)
            if prices is not None and len(prices) > 0:
                all_prices[symbol] = prices
        
        if all_prices:
            return pd.DataFrame(all_prices).dropna()
        return None
    
    def optimize_max_sharpe(self, symbols: list, risk_free_rate: float = 0.05):
        """Optimize portfolio for maximum Sharpe ratio"""
        prices = self.get_price_data(symbols)
        
        if prices is None or prices.empty:
            return None, "Could not fetch price data"
        
        try:
            # Calculate expected returns and covariance
            mu = expected_returns.mean_historical_return(prices)
            cov = risk_models.sample_cov(prices)
            
            # Optimize
            ef = EfficientFrontier(mu, cov)
            weights = ef.max_sharpe(risk_free_rate=risk_free_rate)
            cleaned_weights = ef.clean_weights()
            
            # Get performance
            expected_return, volatility, sharpe = ef.portfolio_performance(risk_free_rate=risk_free_rate)
            
            return {
                "weights": dict(cleaned_weights),
                "expected_return": expected_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe
            }, None
            
        except Exception as e:
            return None, str(e)
    
    def optimize_min_volatility(self, symbols: list):
        """Optimize portfolio for minimum volatility"""
        prices = self.get_price_data(symbols)
        
        if prices is None or prices.empty:
            return None, "Could not fetch price data"
        
        try:
            mu = expected_returns.mean_historical_return(prices)
            cov = risk_models.sample_cov(prices)
            
            ef = EfficientFrontier(mu, cov)
            weights = ef.min_volatility()
            cleaned_weights = ef.clean_weights()
            
            expected_return, volatility, sharpe = ef.portfolio_performance()
            
            return {
                "weights": dict(cleaned_weights),
                "expected_return": expected_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe
            }, None
            
        except Exception as e:
            return None, str(e)
    
    def optimize_target_return(self, symbols: list, target_return: float):
        """Optimize portfolio for a target return"""
        prices = self.get_price_data(symbols)
        
        if prices is None or prices.empty:
            return None, "Could not fetch price data"
        
        try:
            mu = expected_returns.mean_historical_return(prices)
            cov = risk_models.sample_cov(prices)
            
            ef = EfficientFrontier(mu, cov)
            weights = ef.efficient_return(target_return=target_return)
            cleaned_weights = ef.clean_weights()
            
            expected_return, volatility, sharpe = ef.portfolio_performance()
            
            return {
                "weights": dict(cleaned_weights),
                "expected_return": expected_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe
            }, None
            
        except Exception as e:
            return None, str(e)
    
    def get_discrete_allocation(self, weights: dict, total_value: float, prices: dict):
        """Convert weights to actual share amounts"""
        latest_prices = pd.Series(prices)
        
        da = DiscreteAllocation(weights, latest_prices, total_portfolio_value=total_value)
        allocation, leftover = da.greedy_portfolio()
        
        return {
            "shares": allocation,
            "leftover": leftover
        }