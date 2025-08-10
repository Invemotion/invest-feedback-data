# Colab 에서 실행!!
# 의존성: !pip install orjson ujson (선택)
import json, csv
from google.colab import drive
drive.mount('/content/drive')

IN_JSONL  = "/content/drive/MyDrive/your_folder/news_raw_20250805.jsonl"   # ← 로컬에서 올린 파일
OUT_CSV   = "/content/drive/MyDrive/your_folder/news_infer_20250805.csv"

# ---- 읽기(메모리) ----
records = []
with open(IN_JSONL, "r", encoding="utf-8") as f:
    for line in f:
        records.append(json.loads(line))

# ---- 전처리 ----
def basic_preprocess(records):
    seen = set(); out = []
    for r in records:
        if not r.get("content","").strip(): continue
        link = r.get("link"); 
        if link in seen: continue
        seen.add(link)
        if len(r.get("title","")) < 3: continue
        if len(r.get("content","")) < 20: continue
        out.append(r)
    return out

records = basic_preprocess(records)

# ---- 모델 추론: 여러분 모델 연결 ----
def run_model_inference(batch_texts):
    # TODO: 여러분 Colab 환경의 모델 코드로 교체
    # 예: transformers pipeline, 또는 자체 LLM/분류기
    return [{"label":"NEUTRAL","score":0.5} for _ in batch_texts]

batch_texts = [f"[{r['stock_name']}] {r['title']}\n{r['content']}" for r in records]
preds = run_model_inference(batch_texts)

# ---- 결과 merge & 최종 1회 저장 ----
final_rows = [{**r, "pred_label":p["label"], "pred_score":p["score"]} for r,p in zip(records,preds)]

with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=list(final_rows[0].keys()))
    w.writeheader()
    w.writerows(final_rows)

print(f"[완료] 최종 결과 저장: {OUT_CSV} (레코드 {len(final_rows)}건)")
