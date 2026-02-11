from app.database.connection import get_db
from app.database.models import Transaction
from collections import Counter

db = next(get_db())
txs = db.query(Transaction).all()
print(f'Total in DB: {len(txs)}')

months = Counter([t.date.strftime('%Y-%m') for t in txs])
print('\nBy month:')
for m, c in sorted(months.items()):
    print(f'  {m}: {c}')