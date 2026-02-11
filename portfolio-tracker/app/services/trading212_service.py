import os
import requests
import base64
from datetime import datetime
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.database.models import Transaction, TransactionType

load_dotenv()

class Trading212Service:
    def __init__(self, db: Session):
        self.db = db
        self.api_key = os.getenv('TRADING212_API_KEY')
        self.api_key_id = os.getenv('TRADING212_API_KEY_ID')
        self.base_url = "https://live.trading212.com/api/v0"
        
        # Create Basic Auth header
        if self.api_key_id and self.api_key:
            creds = f"{self.api_key_id}:{self.api_key}"
            encoded = base64.b64encode(creds.encode()).decode()
            self.headers = {"Authorization": f"Basic {encoded}"}
        else:
            self.headers = {"Authorization": self.api_key}
    
    def test_connection(self):
        """Test API connection"""
        try:
            response = requests.get(
                f"{self.base_url}/equity/account/cash",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            return {"success": False, "error": f"Status {response.status_code}: {response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_portfolio(self):
        """Get current portfolio positions"""
        try:
            response = requests.get(
                f"{self.base_url}/equity/portfolio",
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
    
    def get_orders_history(self, cursor=None, limit=50):
        """Get historical orders with pagination"""
        try:
            params = {"limit": limit}
            if cursor:
                params["cursor"] = cursor
            
            response = requests.get(
                f"{self.base_url}/equity/history/orders",
                headers=self.headers,
                params=params
            )
            if response.status_code == 200:
                return response.json()
            return {"items": [], "nextPagePath": None}
        except:
            return {"items": [], "nextPagePath": None}
    
    def sync_all_transactions(self, portfolio_id: int):
        """Sync all transactions from Trading212 to database"""
        imported = 0
        skipped = 0
        errors = []
        
        next_url = f"{self.base_url}/equity/history/orders?limit=50"
        
        while next_url:
            try:
                response = requests.get(next_url, headers=self.headers)
                if response.status_code != 200:
                    break
                
                result = response.json()
                items = result.get("items", [])
                
                if not items:
                    break
                
                for item in items:
                    try:
                        order = item.get("order", {})
                        fill = item.get("fill", {})
                        
                        if order.get("status") != "FILLED":
                            continue
                        
                        ticker = order.get("ticker", "")
                        if not ticker:
                            continue
                        
                        # Clean ticker (remove _US_EQ suffix)
                        symbol = ticker.replace("_US_EQ", "").replace("_EQ", "")
                        
                        # Get side from order
                        side = order.get("side", "").upper()
                        if side == "BUY":
                            tx_type = TransactionType.BUY
                        elif side == "SELL":
                            tx_type = TransactionType.SELL
                        else:
                            continue
                        
                        quantity = float(order.get("filledQuantity", 0))
                        price = float(fill.get("price", 0) or order.get("limitPrice", 0) or 0)
                        
                        # Parse date from fill
                        date_str = fill.get("filledAt") or order.get("createdAt")
                        if date_str:
                            tx_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            tx_date = tx_date.replace(tzinfo=None)
                        else:
                            tx_date = datetime.utcnow()
                        
                        # Check for duplicate
                        existing = self.db.query(Transaction).filter(
                            Transaction.portfolio_id == portfolio_id,
                            Transaction.symbol == symbol,
                            Transaction.quantity == quantity,
                            Transaction.price == price,
                            Transaction.date == tx_date
                        ).first()
                        
                        if existing:
                            skipped += 1
                            continue
                        
                        transaction = Transaction(
                            portfolio_id=portfolio_id,
                            symbol=symbol,
                            transaction_type=tx_type,
                            quantity=quantity,
                            price=price,
                            fee=0,
                            date=tx_date
                        )
                        
                        self.db.add(transaction)
                        imported += 1
                        
                    except Exception as e:
                        errors.append(f"Order error: {str(e)}")
                
                # Check for next page
                next_path = result.get("nextPagePath")
                if next_path:
                    next_url = f"https://live.trading212.com{next_path}"
                else:
                    next_url = None
                    
            except Exception as e:
                errors.append(f"Page error: {str(e)}")
                break
        
        self.db.commit()
        
        return {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:20]
        }
    def sync_realized_pnl(self, portfolio_id: int) -> dict:
        """Sync realized P/L from Trading212 order history"""
        from app.database.models import RealizedPnL
        from datetime import datetime
        
        try:
            imported = 0
            skipped = 0
            
            url = "https://live.trading212.com/api/v0/equity/history/orders"
            
            while url:
                response = requests.get(url, headers=self.headers)
                if response.status_code != 200:
                    break
                
                data = response.json()
                
                for item in data.get('items', []):
                    order = item.get('order', {})
                    fill = item.get('fill', {})
                    wallet = fill.get('walletImpact', {})
                    
                    order_id = str(order.get('id', ''))
                    realized = wallet.get('realisedProfitLoss', 0)
                    
                    if not order_id:
                        continue
                    
                    existing = self.db.query(RealizedPnL).filter(
                        RealizedPnL.order_id == order_id
                    ).first()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    order_date = None
                    date_str = order.get('createdAt', '')
                    if date_str:
                        try:
                            order_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            pass
                    
                    ticker = order.get('ticker', '').replace('_US_EQ', '').replace('_EQ', '')
                    
                    pnl_record = RealizedPnL(
                        portfolio_id=portfolio_id,
                        symbol=ticker,
                        order_id=order_id,
                        realized_pnl=realized,
                        order_date=order_date
                    )
                    self.db.add(pnl_record)
                    imported += 1
                
                next_path = data.get('nextPagePath')
                if next_path:
                    url = f"https://live.trading212.com{next_path}"
                else:
                    url = None
            
            self.db.commit()
            return {"success": True, "imported": imported, "skipped": skipped}
        
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}
    def get_realized_pnl_by_symbol(self, portfolio_id: int) -> dict:
        """Get total realized P/L grouped by symbol"""
        from app.database.models import RealizedPnL
        from sqlalchemy import func
        
        results = self.db.query(
            RealizedPnL.symbol,
            func.sum(RealizedPnL.realized_pnl).label('total_pnl')
        ).filter(
            RealizedPnL.portfolio_id == portfolio_id
        ).group_by(RealizedPnL.symbol).all()
        
        return {r.symbol: r.total_pnl for r in results}
    def get_instruments(self) -> dict:
        """Get instrument metadata with company names"""
        try:
            response = requests.get(
                "https://live.trading212.com/api/v0/equity/metadata/instruments",
                headers=self.headers
            )
            if response.status_code == 200:
                instruments = response.json()
                # ticker -> name mapping
                return {i['ticker']: i.get('name', i['ticker']) for i in instruments}
            return {}
        except:
            return {}