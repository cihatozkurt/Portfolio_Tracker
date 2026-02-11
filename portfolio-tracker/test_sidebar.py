from app.services.trading212_service import Trading212Service
from app.database.connection import SessionLocal
from app.services.user_service import UserService

db = SessionLocal()
us = UserService(db)
portfolio = us.get_user_portfolio(1)

t212 = Trading212Service(db)
live_positions = t212.get_portfolio()
realized_by_symbol = t212.get_realized_pnl_by_symbol(portfolio.id)

print(f"Realized P/L dict has {len(realized_by_symbol)} symbols")
print(f"VACQ in dict: {realized_by_symbol.get('VACQ', 'NOT FOUND')}")

# Simulate sidebar logic
for pos in live_positions[:3]:
    ticker = pos.get('ticker', '').replace('_US_EQ', '').replace('_EQ', '')
    unrealized = pos.get('ppl', 0)
    realized = realized_by_symbol.get(ticker, 0)
    total = unrealized + realized
    print(f"{ticker}: Unrealized=${unrealized:.2f}, Realized=${realized:.2f}, Total=${total:.2f}")

db.close()