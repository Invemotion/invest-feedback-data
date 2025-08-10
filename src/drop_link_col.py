import pandas as pd
from pathlib import Path

IN  = "/Users/yujimin/KB AI CHALLENGE/project/data/news/news_20250805_sent_scored.csv"
OUT = IN.replace(".csv", "_nolink.csv")  # 새 파일명

df = pd.read_csv(IN, encoding="utf-8")
if "link" in df.columns:
    df = df.drop(columns=["link"])
else:
    print("⚠️ 'link' 컬럼이 없습니다. 스킵합니다.")

# 새 파일로 저장(엑셀 호환을 위해 UTF-8-SIG)
df.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"✅ Saved → {OUT}  (columns: {list(df.columns)})")

# ── 원본 덮어쓰기 원하면 아래 두 줄 사용 ──
# df.to_csv(IN, index=False, encoding="utf-8-sig")
# print(f"✅ Overwritten → {IN}")
