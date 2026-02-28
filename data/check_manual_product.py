# 수동 등록 상품 API 응답 확인 (leafCategoryId, certificationTargetExcludeContent, productCertificationInfos)
import requests
import time
import bcrypt
import pybase64
import json

client_id = '3gVa5aPCu9eLPpbUaeVBfc'
client_secret = '$2a$04$L20cnXMKIGRwOhr/hdTtuO'

timestamp = str(int((time.time() - 3) * 1000))
password = client_id + '_' + timestamp
hashed = bcrypt.hashpw(password.encode('utf-8'), client_secret.encode('utf-8'))
sign = pybase64.standard_b64encode(hashed).decode('utf-8')

token_res = requests.post('https://api.commerce.naver.com/external/v1/oauth2/token', data={
    'client_id': client_id,
    'timestamp': timestamp,
    'client_secret_sign': sign,
    'grant_type': 'client_credentials',
    'type': 'SELF'
})
token = token_res.json()['access_token']
print('Token OK')

res = requests.get(
    'https://api.commerce.naver.com/external/v2/products/channel-products/13133637343',
    headers={'Authorization': 'Bearer ' + token}
)
print('Status:', res.status_code)

if res.status_code == 200:
    data = res.json()
    origin = data.get('originProduct', {})
    print('leafCategoryId:', origin.get('leafCategoryId'))
    print('name:', origin.get('name'))
    detail = origin.get('detailAttribute', {})
    cert = detail.get('certificationTargetExcludeContent', {})
    print('certExclude:', json.dumps(cert, ensure_ascii=False))
    infos = detail.get('productCertificationInfos', [])
    print('certInfos:', json.dumps(infos, ensure_ascii=False))
else:
    print(res.text[:500])
