import os
import requests
import hashlib
import hmac
import time
from datetime import datetime
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.database.models import Transaction, TransactionType

load_dotenv()

class BinanceService:
    def __init__(self, db: Session):
        self.db = db
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        self.base_url = "https://api.binance.com"
    
    def _sign(self, params: dict) -> str:
        """Create signature for Binance API"""
        query = '&'.join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.secret_key.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _request(self, endpoint: str, params: dict = None):
        """Make signed request to Binance API"""
        if params is None:
            params = {}
        
        params['timestamp'] = int(time.time() * 1000)
        params['signature'] = self._sign(params)
        
        headers = {'X-MBX-APIKEY': self.api_key}
        url = f"{self.base_url}{endpoint}"
        
        response = requests.get(url, params=params, headers=headers)
        return response
    
    def test_connection(self):
        """Test API connection"""
        try:
            response = self._request("/api/v3/account")
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "account_type": data.get("accountType"),
                    "can_trade": data.get("canTrade")
                }
            else:
                return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_account_balances(self):
        """Get all non-zero balances"""
        try:
            response = self._request("/api/v3/account")
            if response.status_code == 200:
                data = response.json()
                balances = []
                for b in data.get("balances", []):
                    free = float(b.get("free", 0))
                    locked = float(b.get("locked", 0))
                    if free > 0 or locked > 0:
                        balances.append({
                            "asset": b["asset"],
                            "free": free,
                            "locked": locked,
                            "total": free + locked
                        })
                return balances
            return []
        except:
            return []
    
    def get_trade_history(self, symbol: str, limit: int = 1000):
        """Get trade history for a specific symbol"""
        try:
            params = {"symbol": symbol, "limit": limit}
            response = self._request("/api/v3/myTrades", params)
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
    
    def get_all_trades(self):
        """Get trades for all traded symbols"""
        try:
            # First get exchange info for all symbols
            info_response = requests.get(f"{self.base_url}/api/v3/exchangeInfo")
            if info_response.status_code != 200:
                return []
            
            symbols = [s["symbol"] for s in info_response.json().get("symbols", [])]
            
            all_trades = []
            # Check common trading pairs first
            common_quotes = ["USDT", "BTC", "EUR", "BUSD", "USDC"]
            
            # Get account balances to find which assets user has traded
            balances = self.get_account_balances()
            user_assets = [b["asset"] for b in balances]
            
            # Also check deposit/withdraw history for assets
            checked_symbols = set()
            
            for asset in user_assets:
                for quote in common_quotes:
                    symbol = f"{asset}{quote}"
                    if symbol in symbols and symbol not in checked_symbols:
                        trades = self.get_trade_history(symbol)
                        all_trades.extend(trades)
                        checked_symbols.add(symbol)
            
            return all_trades
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    def sync_all_transactions(self, portfolio_id: int):
        """Sync all Binance trades to database"""
        imported = 0
        skipped = 0
        errors = []
        
        try:
            trades = self.get_all_trades()
            
            for trade in trades:
                try:
                    symbol = trade.get("symbol", "")
                    qty = float(trade.get("qty", 0))
                    price = float(trade.get("price", 0))
                    is_buyer = trade.get("isBuyer", False)
                    trade_time = trade.get("time", 0)
                    
                    # Parse timestamp
                    tx_date = datetime.fromtimestamp(trade_time / 1000)
                    
                    # Extract base asset from symbol (e.g., BTC from BTCUSDT)
                    base_asset = symbol.replace("USDT", "").replace("EUR", "").replace("BTC", "").replace("BUSD", "")
                    if not base_asset:
                        base_asset = symbol[:3]  # Fallback
                    
                    tx_type = TransactionType.BUY if is_buyer else TransactionType.SELL
                    
                    # Check for duplicate
                    existing = self.db.query(Transaction).filter(
                        Transaction.portfolio_id == portfolio_id,
                        Transaction.symbol == base_asset,
                        Transaction.quantity == qty,
                        Transaction.price == price,
                        Transaction.date == tx_date
                    ).first()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    commission = float(trade.get("commission", 0))
                    
                    transaction = Transaction(
                        portfolio_id=portfolio_id,
                        symbol=base_asset,
                        transaction_type=tx_type,
                        quantity=qty,
                        price=price,
                        fee=commission,
                        date=tx_date
                    )
                    
                    self.db.add(transaction)
                    imported += 1
                    
                except Exception as e:
                    errors.append(f"Trade error: {str(e)}")
            
            self.db.commit()
            
            return {
                "success": True,
                "imported": imported,
                "skipped": skipped,
                "errors": errors[:20]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "imported": 0,
                "skipped": 0
            }