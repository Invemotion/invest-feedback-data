import requests
import json
from datetime import datetime, timedelta
from kis_auth import auth, getTREnv, read_token

# 🔐 인증
auth(svr="vps")
env = getTREnv()
token = env.my_token if env.my_token else read_token()

# 🔍 종목 리스트
stocks = [
    {"name": "삼성전자", "code": "005930"},
    {"name": "NAVER", "code": "035420"},
    {"name": "카카오", "code": "035720"},
    {"name": "현대차", "code": "005380"}
]

# 📅 기본 30일 설정
end_date = datetime.today()
start_date = end_date - timedelta(days=30)

# ✅ 헤더 구성
headers = {
    "authorization": f"Bearer {token}",
    "appkey": env.my_app,
    "appsecret": env.my_sec,
    "tr_id": "FHKST01010400",
    "custtype": "P",
}

# 📦 데이터 저장 딕셔너리
historical_data = {}

# 🔁 종목별 데이터 수집
for stock in stocks:
    print(f"📊 수집 중: {stock['name']}")
    stock_prices = []
    next_date = end_date.strftime("%Y%m%d")

    while True:
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock["code"],
            "fid_org_adj_prc": "0",
            "fid_period_div_code": "D",
            "fid_date": next_date,
        }

        url = f"{env.my_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        response = requests.get(url, headers=headers, params=params)
        result = response.json()

        if result.get("rt_cd") != "0":
            print(f"❌ {stock['name']} 오류: {result.get('msg1')}")
            break

        output = result.get("output", [])
        if not output:
            break

        for item in output:
            date_str = item["stck_bsop_date"]
            if datetime.strptime(date_str, "%Y%m%d") < start_date:
                break  # 수집 범위 벗어남
            stock_prices.append({
                "date": date_str,
                "open": item["stck_oprc"],
                "high": item["stck_hgpr"],
                "low": item["stck_lwpr"],
                "close": item["stck_clpr"],
                "volume": item["acml_vol"],
            })

        # 다음 페이지 요청을 위한 날짜 업데이트
        next_date = output[-1]["stck_bsop_date"]
        if datetime.strptime(next_date, "%Y%m%d") < start_date:
            break

    # 날짜 오름차순 정렬
    historical_data[stock["name"]] = sorted(stock_prices, key=lambda x: x["date"])

# 💾 저장
with open("historical_prices.json", "w", encoding="utf-8") as f:
    json.dump(historical_data, f, indent=2, ensure_ascii=False)

print("✅ 시세 데이터가 historical_prices.json에 저장되었습니다.")
