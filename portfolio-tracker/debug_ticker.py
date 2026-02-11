import requests
import base64
from collections import defaultdict

api_key = '1829052ZQSvqxBgmAQFlmdnVBtvNJnVyKhYj'
secret = 'KtG6QQyDeZB2PfgbIx5bjHz4oYFklH-fdJ3Kvb-iKf8'
creds = base64.b64encode(f'{api_key}:{secret}'.encode()).decode()
headers = {'Authorization': f'Basic {creds}'}

total_orders = 0
page_count = 0
first_date = None
last_date = None

url = 'https://live.trading212.com/api/v0/equity/history/orders'
while url:
    r = requests.get(url, headers=headers)
    data = r.json()
    page_count += 1
    items = data.get('items', [])
    
    for item in items:
        total_orders += 1
        order_date = item.get('order', {}).get('createdAt', '')
        if order_date:
            if first_date is None or order_date < first_date:
                first_date = order_date
            if last_date is None or order_date > last_date:
                last_date = order_date
    
    next_path = data.get('nextPagePath')
    url = f'https://live.trading212.com{next_path}' if next_path else None

print(f"Total pages: {page_count}")
print(f"Total orders: {total_orders}")
print(f"Date range: {first_date[:10] if first_date else 'N/A'} to {last_date[:10] if last_date else 'N/A'}")
print(f"\nBizim DB'de: 1892 transactions, 2025-01-02 to 2025-12-09")