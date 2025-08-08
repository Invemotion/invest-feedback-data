# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import pandas as pd
import os
import time

# ───────────────────────────────
# 1. 설정 영역
# ───────────────────────────────
STOCKS = [
    {"name": "삼성전자", "code": "005930"},
    {"name": "NAVER",   "code": "035420"},
    {"name": "카카오",   "code": "035720"},
    {"name": "현대차",   "code": "005380"},
]
START_DATE = "2025.07.01"
END_DATE   = "2025.07.31"
RESULT_DIR = "./"

timestamp = datetime.now().strftime("%Y%m%d_%H%M")
OUTPUT_FILE = os.path.join(
    RESULT_DIR,
    f"finance_news_{START_DATE.replace('.', '')}_{END_DATE.replace('.', '')}_{timestamp}.csv"
)

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
# 3. 상세 기사 본문 크롤러: JS 리다이렉트 + 본문 선택자
# ───────────────────────────────
def fetch_article_content(link, session, depth=0):
    if depth > 2:
        return ""
    try:
        resp = session.get(link)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        # JS 리다이렉트 페이지 처리
        script = soup.find("script", text=re.compile(r"top\.location\.href"))
        if script:
            m = re.search(r"top\.location\.href\s*=\s*'([^']+)';", script.string)
            if m:
                real_url = m.group(1)
                print(f"    ↳ JS redirect to: {real_url}")
                return fetch_article_content(real_url, session, depth+1)
        # 본문 선택자 우선순위
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
        # 페일백: 전체 텍스트
        return clean_text(soup)
    except Exception as e:
        print(f"    ↳ 본문 에러: {e}")
        return ""

# ───────────────────────────────
# 4. 단일 종목 뉴스 크롤링: 중복 제거
# ───────────────────────────────
def crawl_stock_news(stock_name, stock_code, start_date, end_date):
    base_url = "https://finance.naver.com"
    url_tpl = f"{base_url}/item/news_news.naver?code={stock_code}&page={{page}}&clusterId="

    start_dt = datetime.strptime(start_date, "%Y.%m.%d").date()
    end_dt   = datetime.strptime(end_date, "%Y.%m.%d").date()

    session = requests.Session()
    session.headers.update(HEADERS)

    visited = set()
    page = 1
    collected = []

    while True:
        print(f"[{stock_name}] 페이지 {page}")
        resp = session.get(url_tpl.format(page=page))
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        table = soup.find("table", attrs={"summary": "종목뉴스의 제목, 정보제공, 날짜"})
        if not table:
            print(" [경고] 뉴스 테이블 없음")
            break

        stop = False
        for tr in table.select("tbody > tr"):
            td_date = tr.find("td", class_="date")
            if not td_date:
                continue
            date_only = td_date.get_text(strip=True).split()[0]
            try:
                art_date = datetime.strptime(date_only, "%Y.%m.%d").date()
            except ValueError:
                continue
            if art_date < start_dt:
                stop = True
                break
            if art_date > end_dt:
                continue

            a_tag = tr.find("a", class_="tit")
            info  = tr.find("td", class_="info")
            if not a_tag or not info:
                continue

            href = a_tag["href"]
            # 중복 제거: article_id+office_id 기준
            m = re.search(r"article_id=(\d+).+office_id=(\d+)", href)
            if m:
                aid, oid = m.group(1), m.group(2)
                key = f"{oid}_{aid}"
                if key in visited:
                    continue
                visited.add(key)

            title  = a_tag.get_text(strip=True)
            link   = href if href.startswith("http") else base_url + href
            source = info.get_text(strip=True)

            print(f"  [링크 이동] {link}")
            content = fetch_article_content(link, session)
            if content:
                print(f"  [본문 수집] {title[:30]} → {content[:80]}...")
            else:
                print(f"  [본문 없음] {title[:30]}")
            time.sleep(0.2)

            collected.append({
                "stock_name": stock_name,
                "date":       date_only,
                "title":      title,
                "source":     source,
                "content":    content,
                "link":       link,
            })

        if stop:
            break

        next_btn = soup.select_one("td.pgR > a")
        if next_btn:
            page += 1
            time.sleep(0.3)
        else:
            break

    return collected

# ───────────────────────────────
# 5. 전체 종목 순회 및 저장
# ───────────────────────────────
def main():
    os.makedirs(RESULT_DIR, exist_ok=True)
    all_results = []
    for stock in STOCKS:
        print(f"[크롤링 시작] {stock['name']}({stock['code']})")
        data = crawl_stock_news(stock["name"], stock["code"], START_DATE, END_DATE)
        print(f" [완료] {len(data)}건 수집")
        all_results.extend(data)
    df = pd.DataFrame(all_results)
    if df.empty:
        print("[INFO] 수집된 데이터가 없습니다.")
        return
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"[저장 완료] {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
