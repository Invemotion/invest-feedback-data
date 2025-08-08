# add auto-increasing "id" field at the top of each item in "dummy_trade_history.json"

import json
from collections import OrderedDict

# 기존 JSON 파일 로드
with open('/Users/yujimin/KB AI CHALLENGE/project/data/dummy_trade_history.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# id 필드 추가 및 맨 앞으로 정렬
updated_data = []
for i, trade in enumerate(data, start=1):
    new_trade = OrderedDict()
    new_trade['id'] = i  # id 필드를 맨 앞에 추가
    for key, value in trade.items():
        if key != 'id':  # 기존에 이미 id가 있었다면 제외
            new_trade[key] = value
    updated_data.append(new_trade)

# 새로운 JSON 파일로 저장
with open('dummy_trade_history_with_id.json', 'w', encoding='utf-8') as f:
    json.dump(updated_data, f, ensure_ascii=False, indent=2)

print("✅ 'id' 필드가 맨 앞에 추가되어 저장되었습니다.")
