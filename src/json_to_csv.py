#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JSON → CSV 변환 스크립트
─────────────────────────────────────────────────────────────────────
• 중첩 JSON 평탄화(json_normalize) 지원
• 출력 경로가 없으면 자동으로 생성
• 실행 완료 후 행·열 개수 로그 출력
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd


def json_to_csv(
    json_path: str | Path,
    csv_path: str | Path,
    *,
    flatten: bool = True,
    orient: str = "records",
    encoding: str = "utf-8-sig",
    **to_csv_kwargs: Any,
) -> None:
    """JSON 파일을 CSV로 변환한다."""
    json_path = Path(json_path).expanduser().resolve()
    csv_path = Path(csv_path).expanduser().resolve()

    if not json_path.is_file():
        raise FileNotFoundError(f"[ERROR] 입력 파일이 존재하지 않습니다: {json_path}")

    # ── 1. JSON 로드 ─────────────────────────────────────────────
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # ── 2. DataFrame 변환 & 평탄화 ───────────────────────────────
    if flatten:
        df = pd.json_normalize(data, sep="_")
    else:
        df = pd.DataFrame(data, orient=orient)

    # ── 3. 출력 디렉터리 확보 & CSV 저장 ───────────────────────
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, encoding=encoding, index=False, **to_csv_kwargs)

    print(
        f"[INFO] 변환 완료 ▶ '{json_path.name}' → '{csv_path.name}' "
        f"({len(df):,} rows × {len(df.columns)} cols)"
    )


if __name__ == "__main__":
    # ── 사용자 수정 구간 ───────────────────────────────────────
    JSON_FILE = "/Users/yujimin/KB AI CHALLENGE/project/data/dummy_users.json"
    CSV_FILE = "/Users/yujimin/KB AI CHALLENGE/project/dummy_json_to_csv/dummy_users.csv"
    # ──────────────────────────────────────────────────────────

    try:
        json_to_csv(
            json_path=JSON_FILE,
            csv_path=CSV_FILE,
            flatten=True,          # 중첩 필드 평탄화 여부
            orient="records",      # JSON 형태(기본: 리스트형)
            encoding="utf-8-sig",  # Excel 호환
        )
    except Exception as e:
        print(f"[FAIL] 변환 중 오류 발생: {e}", file=sys.stderr)
        sys.exit(1)
