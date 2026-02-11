from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import Transaction, Portfolio, TransactionType

class PortfolioService:
    def __init__(self, db: Session):
        self.db = db
    
    def add_transaction(self, portfolio_id: int, symbol: str, 
                        transaction_type: str, quantity: float, 
                        price: float, fee: float = 0, date: datetime = None):
        """Add a new buy/sell transaction"""
        if date is None:
            date = datetime.utcnow()
        
        tx_type = TransactionType.BUY if transaction_type.lower() == "buy" else TransactionType.SELL
        
        transaction = Transaction(
            portfolio_id=portfolio_id,
            symbol=symbol.upper(),
            transaction_type=tx_type,
            quantity=quantity,
            price=price,
            fee=fee,
            date=date
        )
        
        self.db.add(transaction)
        self.db.commit()
        return transaction
    
    def get_portfolio_transactions(self, portfolio_id: int):
        """Get all transactions for a portfolio"""
        return self.db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id
        ).order_by(Transaction.date.desc()).all()
    
    def calculate_holdings(self, portfolio_id: int):
        """Calculate current holdings from transactions"""
        transactions = self.get_portfolio_transactions(portfolio_id)
        holdings = {}
        
        for tx in transactions:
            symbol = tx.symbol
            if symbol not in holdings:
                holdings[symbol] = {"quantity": 0, "total_cost": 0, "fees": 0}
            
            if tx.transaction_type == TransactionType.BUY:
                holdings[symbol]["quantity"] += tx.quantity
                holdings[symbol]["total_cost"] += (tx.quantity * tx.price)
                holdings[symbol]["fees"] += tx.fee
            else:  # SELL
                holdings[symbol]["quantity"] -= tx.quantity
        
        # Calculate average cost
        for symbol in holdings:
            qty = holdings[symbol]["quantity"]
            if qty > 0:
                holdings[symbol]["avg_cost"] = holdings[symbol]["total_cost"] / qty
            else:
                holdings[symbol]["avg_cost"] = 0
        
        return holdings
    
    def calculate_realized_pnl(self, portfolio_id: int):
        """Calculate realized PnL using FIFO method"""
        transactions = self.db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id
        ).order_by(Transaction.date.asc()).all()
        
        # FIFO queues per symbol
        buy_queues = {}
        realized_pnl = {}
        
        for tx in transactions:
            symbol = tx.symbol
            if symbol not in buy_queues:
                buy_queues[symbol] = []
                realized_pnl[symbol] = 0
            
            if tx.transaction_type == TransactionType.BUY:
                buy_queues[symbol].append({
                    "quantity": tx.quantity,
                    "price": tx.price
                })
            else:  # SELL
                qty_to_sell = tx.quantity
                sell_price = tx.price
                
                while qty_to_sell > 0 and buy_queues[symbol]:
                    oldest_buy = buy_queues[symbol][0]
                    
                    if oldest_buy["quantity"] <= qty_to_sell:
                        # Use entire buy lot
                        pnl = (sell_price - oldest_buy["price"]) * oldest_buy["quantity"]
                        realized_pnl[symbol] += pnl
                        qty_to_sell -= oldest_buy["quantity"]
                        buy_queues[symbol].pop(0)
                    else:
                        # Partial use of buy lot
                        pnl = (sell_price - oldest_buy["price"]) * qty_to_sell
                        realized_pnl[symbol] += pnl
                        oldest_buy["quantity"] -= qty_to_sell
                        qty_to_sell = 0
        
        return realized_pnl
    
    def calculate_unrealized_pnl(self, holdings: dict, current_prices: dict):
        """Calculate unrealized PnL based on current prices"""
        unrealized_pnl = {}
        
        for symbol, data in holdings.items():
            if data["quantity"] > 0 and symbol in current_prices:
                current_value = data["quantity"] * current_prices[symbol]
                cost_basis = data["total_cost"]
                unrealized_pnl[symbol] = current_value - cost_basis
        
        return unrealized_pnl
    
    def get_portfolio_summary(self, portfolio_id: int, current_prices: dict):
        """Get complete portfolio summary"""
        holdings = self.calculate_holdings(portfolio_id)
        realized_pnl = self.calculate_realized_pnl(portfolio_id)
        unrealized_pnl = self.calculate_unrealized_pnl(holdings, current_prices)
        
        total_value = sum(
            data["quantity"] * current_prices.get(symbol, 0)
            for symbol, data in holdings.items()
            if data["quantity"] > 0
        )
        
        total_cost = sum(
            data["total_cost"]
            for data in holdings.values()
            if data["quantity"] > 0
        )
        
        return {
            "holdings": holdings,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_value": total_value,
            "total_cost": total_cost,
            "total_realized_pnl": sum(realized_pnl.values()),
            "total_unrealized_pnl": sum(unrealized_pnl.values())
        }