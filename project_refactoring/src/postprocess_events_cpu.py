# postprocess_events_cpu.py
# -*- coding: utf-8 -*-
"""
입력:  out/{YYYYMMDD}/news_{yyyymmdd}_sent_scored_{종목}.csv
출력:  events_cpu/{YYYYMMDD}/{종목}.csv   (이벤트 단위, 보기 편한 CSV)
특징:
 - CPU 최적화 (기본: 추출식 메타요약, 문장 단위/종결부호 보정)
 - link 미포함 (가중치 계산에는 사용 가능하나 최종 출력에 제외)
 - 감성 출력 기본: sent_label + sent_conf (간결)
   * --include_sent_dist 옵션 사용 시 pos/neu/neg도 함께 저장
"""

from __future__ import annotations
import argparse, json, math, os, re, sys, unicodedata as ud
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

# ML deps (CPU OK)
from sentence_transformers import SentenceTransformer
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# ==============================
# 기본 파라미터 (CPU 친화)
# ==============================
EMBED_MODEL         = "jhgan/ko-sroberta-multitask"   # CPU 가능
USE_KOBART          = False                           # 기본: 추출식 요약(빠름)
KOBART_MODEL        = "digit82/kobart-summarization"  # --use_kobart 로 켤 수 있음

WINDOW_MIN          = 60     # 시간창(분)
STEP_MIN            = 30     # 슬라이딩 스텝(분)
SIM_THRESHOLD       = 0.80   # 높을수록 군집↓(속도↑)
DBSCAN_MIN_SAMPLES  = 2
TOP_EVENTS          = 10     # 종목×일 이벤트 상한

TARGET_WORDS        = 50     # 메타요약 목표 단어 수
TARGET_TOL          = 12     # 목표 초과 허용치(문장 단위 유지)
MAX_EVIDENCE_LINKS  = 2      # 출력에는 미사용, 내부 가중치에만 활용

NEAR_EVENT_MIN      = 90     # 거래와 이벤트 매핑 허용 범위(분)

SOURCE_WEIGHTS = {
    "연합뉴스": 1.3, "로이터": 1.4, "블룸버그": 1.5, "CNBC": 1.3
}

# ==============================
# 유틸
# ==============================
def log(msg: str):
    print(msg, file=sys.stderr, flush=True)

def norm_text(s: str) -> str:
    s = "" if pd.isna(s) else str(s)
    s = ud.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def to_ts(s: str) -> pd.Timestamp:
    try:
        return pd.to_datetime(s, format="%Y.%m.%d %H:%M")
    except Exception:
        return pd.to_datetime(s, errors="coerce")

def extract_date_token(df: pd.DataFrame) -> str:
    dates = pd.to_datetime(df["datetime"].astype(str).str[:10].str.replace(".", "-"))
    dmin  = dates.min()
    return dmin.strftime("%Y%m%d") if pd.notna(dmin) else "unknown"

def safe_name(s: str) -> str:
    s = str(s).strip()
    s = re.sub(r"[\\/:*?\"<>|]+", "_", s)
    s = re.sub(r"\s+", "_", s)
    return s

def source_weight_from_link(link: str) -> float:
    if not isinstance(link, str): return 1.0
    for k, w in SOURCE_WEIGHTS.items():
        if k in link: return w
    m = re.search(r"https?://([^/]+)/", link)
    if m:
        host = m.group(1)
        if "bloomberg" in host: return 1.5
        if "reuters"   in host: return 1.4
        if "yna"       in host: return 1.3
    return 1.0

# ==============================
# 임베딩/클러스터링 (precomputed 대신 임베딩 직접)
# ==============================
def make_embeddings(model: SentenceTransformer, texts: List[str]) -> np.ndarray:
    return model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)

def dbscan_on_embeddings(emb: np.ndarray, sim_th: float, min_samples: int) -> np.ndarray:
    eps = 1.0 - float(sim_th)  # cosine distance = 1 - cosine_similarity
    cl  = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine", n_jobs=-1)
    labels = cl.fit_predict(emb.astype(np.float64, copy=False))
    return labels

def merge_overlapping_events(groups: List[List[int]], threshold=0.5) -> List[List[int]]:
    groups = [set(g) for g in groups]
    merged = True
    while merged:
        merged = False
        out = []
        used = [False]*len(groups)
        for i in range(len(groups)):
            if used[i]: continue
            base = set(groups[i])
            for j in range(i+1, len(groups)):
                if used[j]: continue
                inter = len(base & groups[j])
                smaller = min(len(base), len(groups[j]))
                if smaller > 0 and inter / smaller >= threshold:
                    base |= groups[j]; used[j] = True; merged = True
            used[i] = True
            out.append(sorted(base))
        groups = [set(g) for g in out]
    return [sorted(g) for g in groups]

def timeboxed_clusters(df: pd.DataFrame,
                       emb_model: SentenceTransformer,
                       window_min=WINDOW_MIN,
                       step_min=STEP_MIN,
                       sim_th=SIM_THRESHOLD) -> List[List[int]]:
    df = df.sort_values("ts").reset_index(drop=True)
    starts, ends = df["ts"].min(), df["ts"].max()
    if pd.isna(starts) or pd.isna(ends):
        return []

    events: List[List[int]] = []
    cur = starts
    while cur <= ends:
        win_mask = (df["ts"] >= cur) & (df["ts"] < cur + pd.Timedelta(minutes=window_min))
        win = df[win_mask]
        if len(win) >= 2:
            emb = make_embeddings(emb_model, win["summary"].tolist())
            labels = dbscan_on_embeddings(emb, sim_th=sim_th, min_samples=DBSCAN_MIN_SAMPLES)
            for lb in sorted(set(labels) - {-1}):
                idxs = win.index[labels == lb].tolist()
                if len(idxs) >= 2:
                    events.append(idxs)
        cur += pd.Timedelta(minutes=step_min)

    covered = set(i for grp in events for i in grp)
    singles = [i for i in df.index.tolist() if i not in covered]
    events += [[i] for i in singles]  # 단일 기사도 이벤트로

    events = merge_overlapping_events(events, threshold=0.5)
    return events

# ==============================
# 추출식 메타요약(문장 단위, 절단 금지)
# ==============================
SENT_SPLIT_RE = re.compile(r"(?<=[.!?\"”’)\]])\s+|(?<=\.)\s+")

def split_sentences(text: str) -> List[str]:
    text = norm_text(text)
    sents = [s.strip() for s in SENT_SPLIT_RE.split(text) if s.strip()]
    return sents

def finalize_sentence(text: str) -> str:
    t = norm_text(text)
    if t and not re.search(r'[.!?\"”’)\]]$', t):
        t += "."
    return t

def extractive_summary(texts: List[str], target_words=TARGET_WORDS, max_sents=5, tol=TARGET_TOL) -> str:
    if not texts: return ""
    big = " ".join(norm_text(t) for t in texts)
    sents = split_sentences(big)
    if len(sents) <= 1:
        return finalize_sentence(big[:400])

    tfv = TfidfVectorizer(max_features=8000)
    X = tfv.fit_transform(sents)  # (S, V) sparse

    # 문서 평균벡터 → 1D ndarray
    doc_vec = X.mean(axis=0)
    if hasattr(doc_vec, "A1"):
        doc_vec = doc_vec.A1
    else:
        doc_vec = np.asarray(doc_vec).ravel()

    from sklearn.metrics.pairwise import cosine_similarity as cos
    sim = cos(X, doc_vec.reshape(1, -1)).ravel()  # (S,)

    # 상위 후보(중복 억제 MMR)
    order = np.argsort(-sim).tolist()
    picked, cand = [], order[:max_sents*3]
    lam = 0.7
    while cand and len(picked) < max_sents:
        best, best_score = None, -1
        for i in cand:
            # 이미 선택된 문장과 최대 유사도 벌점
            red = 0.0
            for j in picked:
                v = cos(X[i], X[j])[0, 0]
                red = max(red, float(v))
            score = lam * float(sim[i]) - (1 - lam) * red
            if score > best_score:
                best, best_score = i, score
        picked.append(best); cand.remove(best)

    picked.sort()  # 원문 순서
    # 목표 단어수에 맞춰 '문장 단위'로 누적 (절단 금지)
    out_sents, wc = [], 0
    for idx in picked:
        sent = sents[idx]
        wc_next = wc + len(sent.split())
        if wc == 0 or wc_next <= target_words + tol:
            out_sents.append(sent); wc = wc_next
        else:
            break
    out = " ".join(out_sents)
    return finalize_sentence(out)

# (옵션) KoBART 생성 요약
def kobart_summarize(texts: List[str], min_new=70, max_new=110) -> str:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
    device = "cpu"
    tok = AutoTokenizer.from_pretrained(KOBART_MODEL)
    model = AutoModelForSeq2SeqLM.from_pretrained(KOBART_MODEL).to(device)
    model.eval()
    big = " ".join(norm_text(t) for t in texts)[:3000]
    enc = tok(big, max_length=1024, truncation=True, return_tensors="pt").to(device)
    enc.pop("token_type_ids", None)
    with torch.inference_mode():
        out = model.generate(**enc, min_new_tokens=min_new, max_new_tokens=max_new,
                             num_beams=4, length_penalty=1.1, no_repeat_ngram_size=3,
                             early_stopping=True)
    s = tok.decode(out[0], skip_special_tokens=True)
    return finalize_sentence(s)

# ==============================
# 이벤트 집계/스코어링/태깅
# ==============================
def event_sentiment(df: pd.DataFrame, idxs: List[int]) -> Dict[str, float]:
    g = df.loc[idxs]
    w = []
    for _, r in g.iterrows():
        w.append(max(float(r.get("pred_conf", 1.0)) * source_weight_from_link(r.get("link","")), 1e-6))
    w = np.array(w); w = w / w.sum()
    neg = float(np.sum(w * g["neg"].astype(float).values))
    neu = float(np.sum(w * g["neu"].astype(float).values))
    pos = float(np.sum(w * g["pos"].astype(float).values))
    label = ["neg","neu","pos"][int(np.argmax([neg,neu,pos]))]
    conf  = float(max(neg, neu, pos))
    return {"neg":neg, "neu":neu, "pos":pos, "label":label, "conf":conf}

def event_time(df: pd.DataFrame, idxs: List[int]) -> pd.Timestamp:
    ts = df.loc[idxs, "ts"].sort_values()
    return ts.iloc[len(ts)//2]

def event_title(df: pd.DataFrame, idxs: List[int]) -> str:
    g = df.loc[idxs]
    scores = []
    for i, r in g.iterrows():
        w = float(r.get("pred_conf", 1.0)) * source_weight_from_link(r.get("link",""))
        scores.append((w * len(norm_text(r.get("summary",""))), i))
    scores.sort(reverse=True)
    top_idx = scores[0][1]
    return norm_text(g.at[top_idx, "summary"])[:120]

TAG_RULES = [
    (r"실적|컨센서스|가이던스|분기|영업이익|매출", "earnings"),
    (r"리콜|결함|품질|안전", "recall"),
    (r"인수|합병|M&A|지분 취득|스핀오프", "mna"),
    (r"제재|규제|과징금|벌금|제소|소송|집단소송", "regulation"),
    (r"신제품|출시|발표|공개", "product"),
    (r"수급|블록딜|자사주|대주주|배당", "flow"),
    (r"환율|금리|경기|물가|CPI|PPI|고용|GDP", "macro"),
    (r"공급망|라인|증설|가동|협력|공급", "supply"),
    (r"인사|지배구조|CEO|사장|대표|이사회", "governance"),
]
def tag_event(text: str) -> List[str]:
    tags = []
    for pat, tag in TAG_RULES:
        if re.search(pat, text): tags.append(tag)
    return list(dict.fromkeys(tags))[:3]  # 중복 제거, 최대 3개

def event_salience(df: pd.DataFrame, idxs: List[int], date_min: pd.Timestamp) -> float:
    g = df.loc[idxs]
    size = math.log1p(len(idxs))
    sent = abs(float(g["pos"].mean() - g["neg"].mean()))
    recency = 1.0 - ((event_time(df, idxs) - date_min).total_seconds() / (60*60*24 + 1e-6))
    recency = max(0.0, min(1.0, recency))
    return 0.4*size + 0.4*sent + 0.2*recency

# ==============================
# 거래 정합(옵션) — CSV 출력에는 매핑 결과 미포함 (리포트 단계에서 활용 권장)
# ==============================
def load_trades(trades_path: Optional[Path]) -> Optional[pd.DataFrame]:
    if not trades_path or not trades_path.exists(): return None
    df = pd.read_csv(trades_path)
    need = {"stock_name", "time"}
    if need - set(df.columns): return None
    df["time"] = df["time"].apply(to_ts)
    return df

# ==============================
# 메인: CSV → 이벤트 DF → 이벤트 CSV
# ==============================
def build_events_from_csv(csv_path: Path, out_path: Path, *,
                          top_events=TOP_EVENTS, window_min=WINDOW_MIN,
                          step_min=STEP_MIN, sim_th=SIM_THRESHOLD,
                          use_kobart=USE_KOBART, include_sent_dist=False):
    log(f"📄 Loading CSV: {csv_path.name}")
    df = pd.read_csv(csv_path)
    need = {"stock_name","datetime","summary","link","neg","neu","pos","pred_label","pred_conf"}
    miss = need - set(df.columns)
    if miss: raise ValueError(f"{csv_path.name} columns missing: {miss}")

    for col in ["summary","link"]:
        df[col] = df[col].apply(norm_text)
    df["ts"] = df["datetime"].apply(to_ts)
    df = df.dropna(subset=["ts"]).reset_index(drop=True)

    date_token = extract_date_token(df)
    stock = str(df["stock_name"].iloc[0])
    stock_token = safe_name(stock)

    # 임베딩 모델
    log("🔄 Loading embedding model (CPU)…")
    emb_model = SentenceTransformer(EMBED_MODEL)

    # 클러스터링
    log(f"🧩 Clustering (window={window_min}m, step={step_min}m, sim_th={sim_th})…")
    groups = timeboxed_clusters(df, emb_model, window_min, step_min, sim_th)
    log(f"→ clusters: {len(groups)}")

    # 이벤트 생성
    date_min = df["ts"].min()
    events_tmp: List[Tuple[float, Dict]] = []
    for idxs in tqdm(groups, desc="Build events"):
        title = event_title(df, idxs)
        texts = df.loc[idxs, "summary"].tolist()
        meta_summary = kobart_summarize(texts, 70, 110) if use_kobart else extractive_summary(texts, TARGET_WORDS, 5, TARGET_TOL)
        sent = event_sentiment(df, idxs)
        ts   = event_time(df, idxs)
        sal  = event_salience(df, idxs, date_min)
        ev = {
            "ts": ts.strftime("%Y-%m-%d %H:%M"),
            "tags": ";".join(tag_event(title + " " + meta_summary)),
            "title": title,
            "meta_summary": meta_summary,
            "sent_label": sent["label"],
            "sent_conf": round(sent["conf"], 4),
            "salience": round(float(sal), 4),
            "n_articles": len(idxs),
        }
        if include_sent_dist:
            ev.update({
                "sent_pos": round(sent["pos"], 4),
                "sent_neu": round(sent["neu"], 4),
                "sent_neg": round(sent["neg"], 4),
            })
        events_tmp.append((sal, ev))

    # 정렬/상위 N
    events_tmp.sort(key=lambda x: x[0], reverse=True)
    events = [ev for _, ev in events_tmp[:top_events]]

    # DF → CSV 저장 (link 없음)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df = pd.DataFrame(events, columns=[
        "ts","tags","title","meta_summary","sent_label","sent_conf","salience","n_articles"
    ] + (["sent_pos","sent_neu","sent_neg"] if include_sent_dist else []))
    out_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    log(f"✅ Saved → {out_path} (events={len(out_df):,})")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_dir", required=True, help="입력 CSV 폴더: out/{YYYYMMDD}")
    ap.add_argument("--date", required=True, help="YYYYMMDD (출력 폴더명)")
    ap.add_argument("--out_root", default="events_cpu", help="출력 루트 폴더")
    ap.add_argument("--top_events", type=int, default=TOP_EVENTS)
    ap.add_argument("--window_min", type=int, default=WINDOW_MIN)
    ap.add_argument("--step_min", type=int, default=STEP_MIN)
    ap.add_argument("--sim_th", type=float, default=SIM_THRESHOLD)
    ap.add_argument("--use_kobart", action="store_true", help="메타요약에 KoBART 사용(느림)")
    ap.add_argument("--include_sent_dist", action="store_true", help="CSV에 pos/neu/neg 확률 포함")
    args = ap.parse_args()

    in_dir  = Path(args.in_dir)
    out_dir = Path(args.out_root) / args.date

    files = sorted(in_dir.glob("news_*_sent_scored_*.csv"))
    if not files:
        log(f"⚠️ no CSV files in {in_dir}")
        return

    for csv_path in files:
        m = re.match(r"news_\d{8}_sent_scored_(.+)\.csv", csv_path.name)
        stock_tok = m.group(1) if m else csv_path.stem
        out_path = out_dir / f"{stock_tok}.csv"
        build_events_from_csv(csv_path, out_path,
                              top_events=args.top_events,
                              window_min=args.window_min,
                              step_min=args.step_min,
                              sim_th=args.sim_th,
                              use_kobart=args.use_kobart,
                              include_sent_dist=args.include_sent_dist)

if __name__ == "__main__":
    main()
