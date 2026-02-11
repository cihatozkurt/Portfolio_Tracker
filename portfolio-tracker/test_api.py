import requests
import base64

api_key='1829052ZQSvqxBgmAQFlmdnVBtvNJnVyKhYj'
secret='KtG6QQyDeZB2PfgbIx5bjHz4oYFklH-fdJ3Kvb-iKf8'
creds=base64.b64encode(f'{api_key}:{secret}'.encode()).decode()
headers={'Authorization': f'Basic {creds}'}

# İlk sayfayı al ve nextPagePath'i göster
r = requests.get('https://live.trading212.com/api/v0/equity/history/orders', headers=headers, params={'limit': 50})
data = r.json()

print(f"Items count: {len(data.get('items', []))}")
print(f"nextPagePath: {data.get('nextPagePath')}")

# İlk birkaç item'ın yapısını göster
if data.get('items'):
    item = data['items'][0]
    print(f"\nFirst item structure:")
    print(f"Order keys: {item.get('order', {}).keys()}")
    print(f"Fill keys: {item.get('fill', {}).keys()}")