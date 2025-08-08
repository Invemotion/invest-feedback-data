# generate_trade_journals_v2.py
# 투자 일지 작성 시 들어갈 더미 데이터 생성 (Enum 기반)

import json
import random

# 📁 매매 기록 파일 로드
with open("data/dummy_trade_history_v2.json", "r", encoding="utf-8") as f:
    trade_data = json.load(f)

journal_entries = []

# 🔖 감정 및 행동 태그 사전 (ENUM 이름 기준)
emotion_map = {
    "BUY": ["EXPECTATION", "CERTAINTY", "ANXIETY"],
    "SELL_PROFIT": ["CERTAINTY", "JOY"],
    "SELL_LOSS": ["REMORSE", "ANXIETY"],
    "SELL_BREAK_EVEN": ["NEUTRAL", "REGRET"]
}

behavior_map = {
    "BUY": ["CHASING_BUY", "DIVIDED_ENTRY", "EMOTIONAL_ENTRY"],
    "SELL_PROFIT": ["STRATEGIC_EXIT", "DIVIDED_SELL"],
    "SELL_LOSS": ["EARLY_SELL", "DELAYED_STOPLOSS"],
    "SELL_BREAK_EVEN": ["MARKET_FOLLOW", "UNSTABLE_SELL"]
}

reason_map = {
    "BUY": [
        "기술적 반등을 기대하고 매수했습니다.",
        "뉴스를 보고 진입했습니다.",
        "평균 단가를 낮추려고 매수했습니다."
    ],
    "SELL_PROFIT": [
        "목표 수익률에 도달해 매도했습니다.",
        "기분 좋게 수익 보고 나왔습니다.",
        "분할매도 전략이 잘 먹혔습니다."
    ],
    "SELL_LOSS": [
        "지지선이 깨져서 손절했습니다.",
        "뉴스에 반응해 급히 매도했습니다.",
        "예상과 다르게 흘러가서 정리했습니다."
    ],
    "SELL_BREAK_EVEN": [
        "더 기다리기엔 불안해서 본전 정리했습니다.",
        "흐름이 애매해서 일단 나왔습니다.",
        "손실 없이 나온 것에 만족합니다."
    ]
}

# 🧪 일지 생성
for i, trade in enumerate(trade_data, start=1):
    trade_id = trade["id"]
    user_id = trade["userId"]
    action_type = trade["actionType"]  # BUY or SELL
    result_type = trade["resultType"]  # PROFIT, LOSS, BREAK_EVEN or None

    if action_type == "BUY":
        key = "BUY"
        result_enum = "NONE"
    elif action_type == "SELL":
        if result_type == "PROFIT":
            key = "SELL_PROFIT"
        elif result_type == "LOSS":
            key = "SELL_LOSS"
        else:
            key = "SELL_BREAK_EVEN"
        result_enum = result_type
    else:
        continue  # 예외 처리

    journal_entry = {
        "journalId": i,
        "tradeId": trade_id,
        "userId": user_id,
        "reason": random.choice(reason_map[key]),
        "emotion": random.choice(emotion_map[key]),
        "behavior": random.choice(behavior_map[key]),
        "resultType": result_enum
    }

    journal_entries.append(journal_entry)

# 💾 저장
with open("data/dummy_trade_journals_v2.json", "w", encoding="utf-8") as f:
    json.dump(journal_entries, f, indent=2, ensure_ascii=False)

print(f"✅ 총 {len(journal_entries)}건의 매매 일지 더미 데이터가 생성되었습니다.")

