# 화장품/미용이 아닌 일반 카테고리(비타민 50000630)로 API 상품 등록 테스트
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

# 50000630 = 생활/건강 > 건강식품 > 비타민 (권한 제한 없는 일반 카테고리)
payload = {
    "originProduct": {
        "statusType": "SALE",
        "saleType": "NEW",
        "leafCategoryId": "50000630",
        "name": "API 테스트 비타민 일반카테고리 확인용",
        "salePrice": 10000,
        "stockQuantity": 1,
        "detailContent": "<p>API 테스트 상품입니다</p>",
        "images": {
            "representativeImage": {
                "url": "https://shop-phinf.pstatic.net/20260218_93/1771421395641PJLrw_JPEG/77102179829427165_1767093570.jpg"
            }
        },
        "deliveryInfo": {
            "deliveryType": "DELIVERY",
            "deliveryAttributeType": "NORMAL",
            "deliveryCompany": "HANJIN",
            "deliveryFee": {
                "deliveryFeeType": "FREE",
                "baseFee": 0,
                "deliveryFeePayType": "PREPAID",
                "deliveryFeeByArea": {
                    "deliveryAreaType": "AREA_2",
                    "area2extraFee": 3000,
                    "area3extraFee": 3000
                }
            },
            "claimDeliveryInfo": {
                "returnDeliveryFee": 3500,
                "exchangeDeliveryFee": 6000
            }
        },
        "detailAttribute": {
            "afterServiceInfo": {
                "afterServiceTelephoneNumber": "010-7253-0101",
                "afterServiceGuideContent": "상품상세참조"
            },
            "originAreaInfo": {
                "originAreaCode": "0200037",
                "content": "상세설명참조",
                "importer": "상세페이지참조"
            },
            "minorPurchasable": True,
            "certificationTargetExcludeContent": {
                "kcCertifiedProductExclusionYn": "TRUE"
            },
            "productInfoProvidedNotice": {
                "productInfoProvidedNoticeType": "ETC",
                "etc": {
                    "returnCostReason": "상품상세참조",
                    "noRefundReason": "상품상세참조",
                    "qualityAssuranceStandard": "상품상세참조",
                    "compensationProcedure": "상품상세참조",
                    "troubleShootingContents": "상품상세참조",
                    "itemName": "비타민",
                    "modelName": "테스트",
                    "manufacturer": "상품상세참조",
                    "afterServiceDirector": "010-7253-0101"
                }
            }
        }
    },
    "smartstoreChannelProduct": {
        "naverShoppingRegistration": True,
        "channelProductDisplayStatusType": "ON"
    }
}

res = requests.post(
    'https://api.commerce.naver.com/external/v2/products',
    headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
    json=payload
)
print('Status:', res.status_code)
print(res.text[:500])
