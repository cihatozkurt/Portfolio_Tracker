from alpha_vantage.timeseries import TimeSeries
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config import Config

class PriceService:
    def __init__(self):
        self.ts = TimeSeries(key=Config.ALPHA_VANTAGE_API_KEY)
    
    def get_current_price(self, symbol: str):
        """Get current price for a symbol"""
        try:
            data, meta = self.ts.get_quote_endpoint(symbol.upper())
            return {
                "symbol": data["01. symbol"],
                "price": float(data["05. price"]),
                "change": float(data["09. change"]),
                "change_percent": data["10. change percent"],
                "volume": int(data["06. volume"])
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_multiple_prices(self, symbols: list):
        """Get prices for multiple symbols"""
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_current_price(symbol)
        return prices