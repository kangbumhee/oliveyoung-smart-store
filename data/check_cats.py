import requests, time, bcrypt, pybase64, json

client_id = '3gVa5aPCu9eLPpbUaeVBfc'
client_secret = '$2a$04$L20cnXMKIGRwOhr/hdTtuO'

timestamp = str(int((time.time() - 3) * 1000))
password = client_id + '_' + timestamp
hashed = bcrypt.hashpw(password.encode('utf-8'), client_secret.encode('utf-8'))
sign = pybase64.standard_b64encode(hashed).decode('utf-8')

token_res = requests.post('https://api.commerce.naver.com/external/v1/oauth2/token', data={
    'client_id': client_id, 'timestamp': timestamp,
    'client_secret_sign': sign, 'grant_type': 'client_credentials', 'type': 'SELF'
})
token = token_res.json()['access_token']

res = requests.post('https://api.commerce.naver.com/external/v1/products/search',
    headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
    json={'filter': {'statusType': 'SALE'}, 'page': 1, 'size': 50})

data = res.json()
cats = set()
for item in data.get('contents', []):
    for cp in item.get('channelProducts', []):
        cats.add(cp.get('categoryId', '') + ' - ' + cp.get('wholeCategoryName', ''))
for c in sorted(cats):
    print(c)
