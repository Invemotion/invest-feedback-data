# generate_trade_journals.py
# 투자 일지 작성 시 들어갈 더미 데이터 생성

# 수정사항
# journalId는 uuid4() 대신 1부터 자동 증가하는 정수값으로 부여
# tradeId 필드는 dummy_trade_history_with_id.json의 "id" 값을 사용


import json
import random
import uuid

# 📁 매매 기록 파일 로드
with open("/Users/yujimin/KB AI CHALLENGE/project/data/dummy_trade_history_with_id.json", "r", encoding="utf-8") as f:
    trade_data = json.load(f)

journal_entries = []

# 🔖 감정 및 행동 태그 사전
emotion_map = {
    "매수": ["기대", "확신", "불안"],
    "매도_수익": ["확신", "기쁨"],
    "매도_손실": ["후회", "불안"],
    "매도_본전": ["무감정", "아쉬움"]
}

behavior_map = {
    "매수": ["추격매수", "분할진입", "감정적 진입"],
    "매도_수익": ["전략적 정리", "분할매도"],
    "매도_손실": ["조기매도", "손절지연"],
    "매도_본전": ["시장 추종", "불안정 매도"]
}

reason_map = {
    "매수": [
        "기술적 반등을 기대하고 매수했습니다.",
        "뉴스를 보고 진입했습니다.",
        "평균 단가를 낮추려고 매수했습니다."
    ],
    "매도_수익": [
        "목표 수익률에 도달해 매도했습니다.",
        "기분 좋게 수익 보고 나왔습니다.",
        "분할매도 전략이 잘 먹혔습니다."
    ],
    "매도_손실": [
        "지지선이 깨져서 손절했습니다.",
        "뉴스에 반응해 급히 매도했습니다.",
        "예상과 다르게 흘러가서 정리했습니다."
    ],
    "매도_본전": [
        "더 기다리기엔 불안해서 본전 정리했습니다.",
        "흐름이 애매해서 일단 나왔습니다.",
        "손실 없이 나온 것에 만족합니다."
    ]
}

# 🧪 일지 생성
for i, trade in enumerate(trade_data, start=1):
    trade_id = trade["id"]  # ✅ JSON 내 id 필드를 tradeId로 사용
    user_id = trade["userId"]
    action_type = trade["actionType"]
    result_type = trade["resultType"]

    # 매수 / 매도 분기
    if action_type == "매수":
        key = "매수"
    elif action_type == "매도":
        if result_type == "수익":
            key = "매도_수익"
        elif result_type == "손실":
            key = "매도_손실"
        else:
            key = "매도_본전"
    else:
        continue  # 예외 처리

    journal_entry = {
        "journalId": i,  # ✅ 자동 증가 정수값
        "tradeId": trade_id,  # ✅ 기존 UUID 대신 trade의 id 필드 사용
        "userId": user_id,
        "reason": random.choice(reason_map[key]),
        "emotion": random.choice(emotion_map[key]),
        "behavior": random.choice(behavior_map[key]),
        "resultType": result_type if action_type == "매도" else None
    }

    journal_entries.append(journal_entry)

# 💾 저장
with open("dummy_trade_journals_2.json", "w", encoding="utf-8") as f:
    json.dump(journal_entries, f, indent=2, ensure_ascii=False)

print(f"✅ 총 {len(journal_entries)}건의 매매 일지 더미 데이터가 생성되었습니다.")
