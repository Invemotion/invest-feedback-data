# ─────────────────────────────────────────────────────────
# finance_news_crawling.py (v1)
# 목적: 네이버 금융 ‘종목별 뉴스’ 목록을 날짜 범위로 순회하여
#       제목/언론사/링크/본문을 수집하고 CSV로 저장하는 기본 크롤러.
# 특징: 단순 본문 선택자(#articleBodyContents, div#contents article#dic_area) 기반.
# ─────────────────────────────────────────────────────────


# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import pandas as pd
import os
import time

# ——————————————————————————————————————————
# 1. 설정 영역
# ——————————————————————————————————————————
STOCKS = [
    {"name": "삼성전자", "code": "005930"},
    {"name": "NAVER",   "code": "035420"},
    {"name": "카카오",   "code": "035720"},
    {"name": "현대차",   "code": "005380"},
]
START_DATE = "2025.08.01"
END_DATE   = "2025.08.31"
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

# ——————————————————————————————————————————
# 2. 본문 정제 함수
# ——————————————————————————————————————————
def clean_text(html_fragment):
    if html_fragment is None:
        return ""
    text = re.sub(r'<[^>]+>', '', str(html_fragment))
    return text.strip()

# ——————————————————————————————————————————
# 3. 단일 종목 뉴스 크롤러
# ——————————————————————————————————————————
def crawl_stock_news(stock_name, stock_code, start_date, end_date):
    base_url = "https://finance.naver.com"
    url_tpl = f"{base_url}/item/news_news.naver?code={stock_code}&page={{page}}&clusterId="

    start_dt = datetime.strptime(start_date, "%Y.%m.%d").date()
    end_dt   = datetime.strptime(end_date, "%Y.%m.%d").date()

    session = requests.Session()
    session.headers.update(HEADERS)

    page = 1
    collected = []

    while True:
        print(f"[{stock_name}] 페이지 {page}")
        url = url_tpl.format(page=page)
        resp = session.get(url)
        resp.encoding = "euc-kr"
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
            full_dt = td_date.get_text(strip=True)
            date_only = full_dt.split()[0]
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

            title  = a_tag.get_text(strip=True)
            link   = a_tag["href"]
            link   = link if link.startswith("http") else base_url + link
            source = info.get_text(strip=True)

            # 본문 크롤링
            content = ""
            try:
                art_resp = session.get(link)
                art_resp.encoding = "utf-8"
                art_soup = BeautifulSoup(art_resp.text, "html.parser")
                body = art_soup.select_one("#articleBodyContents") \
                    or art_soup.select_one("div#contents article#dic_area")
                content = clean_text(body)
                print(f" [본문 수집] {content[:100]}...")  # 본문 일부 출력
                time.sleep(0.2)
            except Exception as e:
                print(f" [본문 에러] {e}")

            collected.append({
                "stock_name": stock_name,
                "date": date_only,
                "title": title,
                "source": source,
                "content": content,
                "link": link,
            })

        if stop:
            break

        # 다음 버튼이 없으면 종료
        next_btn = soup.select_one("td.pgR > a")
        if next_btn:
            page += 1
            time.sleep(0.3)
        else:
            break

    return collected

# ——————————————————————————————————————————
# 4. 전체 종목 순회 및 저장
# ——————————————————————————————————————————
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

# ——————————————————————————————————————————
# 5. 실행
# ——————————————————————————————————————————
if __name__ == "__main__":
    main()
