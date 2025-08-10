# ─────────────────────────────────────────────────────────
# finance_news_crawling_v3.1.py (v3.1)
# 변경점(대비 v3)
# - 페이징 상한 도입: MAX_PAGES로 최대 페이지 제한(무한 크롤 방지).
# - 저장 방식 변경: 종목별 개별 CSV로 즉시 스트리밍 저장(csv.writer) → 메모리 사용량 감소.
# - 출력 스키마 수정: 날짜 컬럼을 'YYYY.MM.DD HH:MM' 형태(date_time)로 수집(분 단위 확보).
# - 결과 경로 분리: ./results 폴더에 {종목명}_{timestamp}.csv로 저장.
# - 수집 흐름 단순화: START/END 날짜 필터 제거, 테이블 소진 또는 MAX_PAGES 도달 시 종료.
# - 유지/재사용: JS 리다이렉트 추적, 본문 선택자 우선순위, 중복 제거(office_id+article_id)는 동일.
# 참고: pandas 임포트는 저장 단계에서 사용하지 않으므로 제거 가능.
# ─────────────────────────────────────────────────────────


# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import pandas as pd
import os
import time
import csv

# ───────────────────────────────
# 1. 설정 영역
# ───────────────────────────────
STOCKS = [
    {"name": "삼성전자", "code": "005930"},
    {"name": "NAVER",   "code": "035420"},
    {"name": "카카오",   "code": "035720"},
    {"name": "현대차",   "code": "005380"},
]
MAX_PAGES = 200
RESULT_DIR = "./results"

timestamp = datetime.now().strftime("%Y%m%d_%H%M")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
}

# ───────────────────────────────
# 2. 본문 정제 함수
# ───────────────────────────────
def clean_text(html_fragment):
    if html_fragment is None:
        return ""
    text = re.sub(r'<[^>]+>', '', str(html_fragment))
    return text.strip()

# ───────────────────────────────
# 3. 상세 기사 본문 크롤러
# ───────────────────────────────
def fetch_article_content(link, session, depth=0):
    if depth > 2:
        return ""
    try:
        resp = session.get(link)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        script = soup.find("script", text=re.compile(r"top\.location\.href"))
        if script:
            m = re.search(r"top\.location\.href\s*=\s*'([^']+)';", script.string)
            if m:
                real_url = m.group(1)
                print(f"    ↳ JS redirect to: {real_url}")
                return fetch_article_content(real_url, session, depth+1)

        selectors = [
            "#articleBodyContents",
            "div#contents .newsct_body",
            "article#dic_area",
            "div.newsct_body",
        ]
        for sel in selectors:
            body = soup.select_one(sel)
            if body:
                print(f"    ↳ 본문 컨테이너 발견: {sel}")
                return clean_text(body)
        return clean_text(soup)
    except Exception as e:
        print(f"    ↳ 본문 에러: {e}")
        return ""

# ───────────────────────────────
# 4. 종목별 뉴스 크롤링 함수
# ───────────────────────────────
def crawl_stock_news(stock_name, stock_code, csv_writer):
    base_url = "https://finance.naver.com"
    url_tpl = f"{base_url}/item/news_news.naver?code={stock_code}&page={{page}}&clusterId="

    session = requests.Session()
    session.headers.update(HEADERS)

    visited = set()
    for page in range(1, MAX_PAGES + 1):
        print(f"[{stock_name}] 페이지 {page}")
        resp = session.get(url_tpl.format(page=page))
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        table = soup.find("table", attrs={"summary": "종목뉴스의 제목, 정보제공, 날짜"})
        if not table:
            print(" [경고] 뉴스 테이블 없음")
            break

        rows = table.select("tbody > tr")
        if not rows:
            print(" [정보] 더 이상 뉴스 없음")
            break

        for tr in rows:
            td_date = tr.find("td", class_="date")
            if not td_date:
                continue

            # date_only = td_date.get_text(strip=True).split()[0]
            date_time = " ".join(td_date.stripped_strings) # 시간:분까지 가져옴
            
            print(date_time)

            a_tag = tr.find("a", class_="tit")
            info  = tr.find("td", class_="info")
            if not a_tag or not info:
                continue

            href = a_tag["href"]
            m = re.search(r"article_id=(\d+).+office_id=(\d+)", href)
            if m:
                aid, oid = m.group(1), m.group(2)
                key = f"{oid}_{aid}"
                if key in visited:
                    continue
                visited.add(key)

            title = a_tag.get_text(strip=True)
            link  = href if href.startswith("http") else base_url + href
            source = info.get_text(strip=True)

            print(f"  [링크 이동] {link}")
            content = fetch_article_content(link, session)
            if content:
                print(f"  [본문 수집] {title[:30]} → {content[:60]}...")
            else:
                print(f"  [본문 없음] {title[:30]}")
            time.sleep(0.2)

            row = [
                stock_name,
                date_time,
                title,
                source,
                content,
                link,
            ]
            csv_writer.writerow(row)

# ───────────────────────────────
# 5. 메인 실행 함수
# ───────────────────────────────
def main():
    os.makedirs(RESULT_DIR, exist_ok=True)
    for stock in STOCKS:
        filename = os.path.join(
            RESULT_DIR,
            f"{stock['name']}_{timestamp}.csv"
        )
        print(f"\n[크롤링 시작] {stock['name']}({stock['code']}) → 저장: {filename}")
        with open(filename, "w", encoding="utf-8-sig", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["stock_name", "date", "title", "source", "content", "link"])
            crawl_stock_news(stock["name"], stock["code"], writer)
        print(f"[완료] {stock['name']} 저장 완료\n")

if __name__ == "__main__":
    main()
