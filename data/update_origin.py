"""이전 등록 상품들의 원산지 정보(originAreaCode 03)로 업데이트"""
import requests
from naver.commerce_auth import naver_auth

products = ["13075636382", "13075637134", "13075515129"]
for pno in products:
    payload = {
        "originProduct": {
            "detailAttribute": {
                "originAreaInfo": {
                    "originAreaCode": "03",
                    "content": "상세설명에 표시",
                    "importer": "상세페이지 참조",
                }
            }
        }
    }
    r = requests.put(
        f"https://api.commerce.naver.com/external/v2/products/{pno}",
        json=payload,
        headers=naver_auth.headers,
    )
    print(f"{pno}: {r.status_code}")
