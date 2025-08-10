# run_local_export_jsonl.py
# -*- coding: utf-8 -*-
import json
from pathlib import Path
from crawler_core import crawl_many

STOCKS = [
    {"name": "삼성전자", "code": "005930"},
    {"name": "NAVER",   "code": "035420"},
    {"name": "카카오",   "code": "035720"},
    {"name": "현대차",   "code": "005380"},
]

TARGET_DATE = "2025.08.05"  # YYYY.MM.DD
OUT_ROOT   = Path("./news_raw")  # 루트 디렉터리

def safe_filename(name: str) -> str:
    """파일/폴더명 안전화: 금지문자 제거, 공백 압축"""
    import re
    s = str(name).strip()
    s = re.sub(r"[\\/:*?\"<>|]+", "_", s)  # 금지문자 → _
    s = re.sub(r"\s+", "_", s)             # 다중 공백 → _
    return s

def date_token(date_str: str) -> str:
    """'2025.08.05' → '20250805'"""
    return date_str.replace(".", "")

def main():
    dt_tok = date_token(TARGET_DATE)
    day_dir = OUT_ROOT / dt_tok
    day_dir.mkdir(parents=True, exist_ok=True)

    for stock in STOCKS:
        stock_name = stock["name"]
        print(f"\n📌 [{stock_name}] {TARGET_DATE} 뉴스 크롤링 시작...")
        
        fname = f"{safe_filename(stock_name)}.jsonl"
        out_path = day_dir / fname

        count = 0
        with open(out_path, "w", encoding="utf-8") as f:
            for r in crawl_many([stock], TARGET_DATE, max_pages=200):
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                count += 1
                # 10건 단위로 진행 상황 표시
                if count % 10 == 0:
                    print(f"  ├─ 진행: {count}건 수집 완료")
        
        print(f"✅ [{stock_name}] 완료: {count}건 저장 → {out_path}")

if __name__ == "__main__":
    main()
