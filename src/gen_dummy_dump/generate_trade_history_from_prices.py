# generate_trade_history_from_prices.py
# 실제 주식 시세 기반으로 유저별 더미 매매 데이터 생성

import json
import random
from datetime import datetime, timedelta
import uuid

# ✅ 사용자 프로필 정의 (성향에 따라 거래 패턴을 달리함)
user_profiles = {
    "user_001": {"type": "conservative"},
    "user_002": {"type": "neutral"},
    "user_003": {"type": "aggressive"},
}

# ✅ 성향별 거래 수량 설정
def get_quantity(profile_type):
    if profile_type == "conservative":
        return random.randint(1, 10)
    elif profile_type == "neutral":
        return random.randint(5, 30)
    elif profile_type == "aggressive":
        return random.randint(20, 50)

# ✅ 성향별 거래 빈도 설정
def get_daily_trade_count(profile_type):
    if profile_type == "conservative":
        return random.choices([0, 1], weights=[0.3, 0.7])[0]  # 간헐적 거래
    elif profile_type == "neutral":
        return random.randint(1, 2)
    elif profile_type == "aggressive":
        return random.randint(1, 3)

# ✅ 거래 시간 생성 (장중 랜덤)
def random_order_time(base_date):
    start = base_date.replace(hour=9, minute=0)
    end = base_date.replace(hour=15, minute=30)
    delta = end - start
    rand_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=rand_seconds)

# ✅ 매매 기록 생성 함수
def generate_trade_record(stock_name, stock_code, price_info, user_id, profile_type):
    base_date = datetime.strptime(price_info["date"], "%Y%m%d")
    order_time = random_order_time(base_date)
    completion_time = order_time + timedelta(minutes=random.randint(1, 5))

    action_type = random.choice(["매수", "매도"])
    order_type = random.choice(["시장가", "지정가"])
    price = int(price_info["open"]) + random.randint(-300, 300)
    quantity = get_quantity(profile_type)

    return {
        "userId": user_id,
        "userProfile": profile_type,
        "tradeId": str(uuid.uuid4()),
        "stockName": stock_name,
        "stockCode": stock_code,
        "actionType": action_type,
        "orderType": order_type,
        "orderTime": order_time.strftime("%Y-%m-%d %H:%M:%S"),
        "completionTime": completion_time.strftime("%Y-%m-%d %H:%M:%S"),
        "marketPriceAtOrder": price,
        "pricePerBuy": price if action_type == "매수" else None,
        "pricePerSell": price if action_type == "매도" else None,
        "quantity": quantity,
        "totalAmount": price * quantity,
        "resultType": None if action_type == "매수" else random.choice(["손실", "수익", "본전"]),
        "exchangeRate": None
    }

# ✅ 종목 코드 맵
stock_code_map = {
    "삼성전자": "005930",
    "NAVER": "035420",
    "카카오": "035720",
    "현대차": "005380"
}

# ✅ 시세 데이터 로드
with open("historical_prices.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# ✅ 더미 매매 기록 생성
dummy_trades = []

for user_id, profile in user_profiles.items():
    profile_type = profile["type"]
    for stock_name, price_list in raw_data.items():
        stock_code = stock_code_map.get(stock_name, "000000")
        for price_info in price_list:
            daily_count = get_daily_trade_count(profile_type)
            for _ in range(daily_count):
                trade = generate_trade_record(
                    stock_name, stock_code, price_info, user_id, profile_type
                )
                dummy_trades.append(trade)

# ✅ 저장
with open("dummy_trade_history.json", "w", encoding="utf-8") as f:
    json.dump(dummy_trades, f, indent=2, ensure_ascii=False)

print(f"✅ 총 {len(dummy_trades)}건의 더미 매매 기록이 생성되었습니다.")
