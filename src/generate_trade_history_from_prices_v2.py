# generate_trade_history_from_prices_v2.py
# 실제 주식 시세 기반으로 유저별 더미 매매 데이터 생성 (enum 반영)

"""
| 고려 요소                   | 반영 위치 설명                                                                 |
|----------------------------|------------------------------------------------------------------------------|
| **type** (user 성향)       | 거래 수량(`get_quantity`) 및 거래 빈도(`get_daily_trade_count`) 결정 기준으로 사용         |
| **income** (소득 수준)     | `get_quantity`: 소득 높을수록 거래 수량 증가                                              |
| **investment duration**    | `get_daily_trade_count`: 장기 보유일수록 거래 빈도 감소                                     |
| **investment goal**        | `decide_action_type`: 보수적 목표일수록 매수 확률 증가, 공격적 목표일수록 매도 확률 증가         |
| **기록 필드 설명**         | `userProfile` 제거됨. 기록에는 `userId`만 포함됨                                        |
"""

import json
import random
from datetime import datetime, timedelta
import uuid

# ✅ 사용자 정보 로드
with open("data/dummy_users.json", "r", encoding="utf-8") as f:
    user_data = json.load(f)

# ✅ 필요한 속성만 정리
user_profiles = {
    user["userId"]: {
        "type": user["profile"],
        "income": user["annualIncome"],
        "goal": user["investmentGoal"],
        "duration": user["investmentPeriod"]
    }
    for user in user_data
}

# ✅ 한글 -> ENUM 매핑 정의
ACTION_TYPE_MAP = {"매수": "BUY", "매도": "SELL"}
ORDER_TYPE_MAP = {"시장가": "MARKET", "지정가": "LIMIT"}
RESULT_TYPE_MAP = {"수익": "PROFIT", "손실": "LOSS", "본전": "BREAK_EVEN"}

# ✅ 성향 + 소득에 따른 거래 수량 설정
def get_quantity(profile):
    base = {
        "CONSERVATIVE": (1, 5),
        "NEUTRAL": (5, 20),
        "AGGRESSIVE": (20, 50)
    }[profile["type"]]

    income_bonus = {
        "OVER_100_MILLION": 10,
        "UNDER_100_MILLION": 5,
        "UNDER_30_MILLION": 0,
        "UNDER_10_MILLION": 0
    }.get(profile.get("income"), 0)

    return random.randint(base[0], base[1]) + income_bonus

# ✅ 성향 + 투자 기간에 따른 거래 빈도 설정
def get_daily_trade_count(profile):
    type_base = {
        "CONSERVATIVE": [0, 1],
        "NEUTRAL": [1, 2],
        "AGGRESSIVE": [2, 4]
    }[profile["type"]]

    duration_penalty = {
        "LESS_THAN_6_MONTHS": 0,
        "LESS_THAN_1_YEAR": 0,
        "BETWEEN_1_AND_2_YEARS": -1,
        "OVER_3_YEARS": -2
    }.get(profile.get("duration"), 0)

    max_count = max(type_base[1] + duration_penalty, 1)
    return random.randint(type_base[0], max_count)

# ✅ 거래 시간 생성 (장중 랜덤)
def random_order_time(base_date):
    start = base_date.replace(hour=9, minute=0)
    end = base_date.replace(hour=15, minute=30)
    delta = end - start
    rand_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=rand_seconds)

# ✅ 매도/매수 로직 확장: 투자 목표 기반
def decide_action_type(profile):
    goal = profile.get("goal", "TRACK_MARKET_RETURN")
    duration = profile.get("duration", "LESS_THAN_1_YEAR")

    if goal == "HIGH_RISK_HIGH_RETURN" and duration == "LESS_THAN_1_YEAR":
        return random.choices(["매도", "매수"], weights=[0.6, 0.4])[0]
    elif goal == "STABLE_INCOME" and duration == "OVER_3_YEARS":
        return random.choices(["매수", "매도"], weights=[0.7, 0.3])[0]
    else:
        return random.choice(["매수", "매도"])

# ✅ 매매 기록 생성 함수
def generate_trade_record(stock_name, stock_code, price_info, user_id, profile):
    base_date = datetime.strptime(price_info["date"], "%Y%m%d")
    order_time = random_order_time(base_date)
    completion_time = order_time + timedelta(minutes=random.randint(1, 5))

    action_kor = decide_action_type(profile)
    order_kor = random.choice(["시장가", "지정가"])
    result_kor = None if action_kor == "매수" else random.choice(["수익", "손실", "본전"])

    price = int(price_info["open"]) + random.randint(-300, 300)
    quantity = get_quantity(profile)

    return {
        "userId": user_id,
        "tradeUUID": str(uuid.uuid4()),
        "stockName": stock_name,
        "stockCode": stock_code,
        "actionType": ACTION_TYPE_MAP[action_kor],  # ✅ ENUM 적용
        "orderType": ORDER_TYPE_MAP[order_kor],     # ✅ ENUM 적용
        "orderTime": order_time.strftime("%Y-%m-%d %H:%M:%S"),
        "completionTime": completion_time.strftime("%Y-%m-%d %H:%M:%S"),
        "marketPriceAtOrder": price,
        "pricePerBuy": price if action_kor == "매수" else None,
        "pricePerSell": price if action_kor == "매도" else None,
        "quantity": quantity,
        "totalAmount": price * quantity,
        "resultType": RESULT_TYPE_MAP[result_kor] if result_kor else None,  # ✅ ENUM 적용
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
with open("data/historical_prices.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# ✅ 더미 매매 기록 생성
dummy_trades = []
id_counter = 1

for user_id, profile in user_profiles.items():
    for stock_name, price_list in raw_data.items():
        stock_code = stock_code_map.get(stock_name, "000000")
        for price_info in price_list:
            daily_count = get_daily_trade_count(profile)
            for _ in range(daily_count):
                trade = generate_trade_record(stock_name, stock_code, price_info, user_id, profile)
                trade["id"] = id_counter
                id_counter += 1
                dummy_trades.append(trade)

# ✅ 저장
with open("data/dummy_trade_history_v2.json", "w", encoding="utf-8") as f:
    json.dump(dummy_trades, f, indent=2, ensure_ascii=False)

print(f"✅ 총 {len(dummy_trades)}건의 더미 매매 기록이 생성되었습니다.")
