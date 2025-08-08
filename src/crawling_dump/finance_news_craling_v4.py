# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import time
import os
import re
import requests

# ───────────────────────────────────────────────────
# 1. 설정 영역
# ───────────────────────────────────────────────────
STOCKS = [
    {"name": "삼성전자", "keywords": ["삼성전자", "삼성전자 주가", "삼성전자 뉴스"]},
    {"name": "NAVER", "keywords": ["NAVER", "NAVER 주가", "NAVER 뉴스"]},
    {"name": "카카오", "keywords": ["카카오", "카카오 주가", "카카오 뉴스"]},
    {"name": "현대차", "keywords": ["현대차", "현대차 주가", "현대차 뉴스"]},
]

RESULT_PATH = './results'
os.makedirs(RESULT_PATH, exist_ok=True)

# ───────────────────────────────────────────────────
# 2. 본문 정제 함수
# ───────────────────────────────────────────────────
def clean_text(html_fragment):
    if not html_fragment:
        return ""
    text = re.sub(r'<[^>]+>', '', str(html_fragment))
    return text.strip()

# ───────────────────────────────────────────────────
# 3. 본문 크롤링 함수
# ───────────────────────────────────────────────────
def fetch_article_content(url):
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        selectors = [
            "#dic_area", "#articleBodyContents", "div#contents .newsct_body", "article#dic_area"
        ]
        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                print(f"    ↳ 본문 selector '{sel}' 성공")
                return clean_text(node)
        print("    ↳ 본문 추출 실패")
        return ""
    except Exception as e:
        return f"[본문 오류] {e}"

# ───────────────────────────────────────────────────
# 4. 뉴스 리스트 + 본문 수집 함수
# ───────────────────────────────────────────────────
def crawler_with_scroll(keyword, start_date, end_date, sort, output_file, max_scroll=5):
    options = Options()
    options.add_argument('--disable-gpu')
    # options.add_argument('--headless')  # 디버깅 시엔 주석 처리
    driver = webdriver.Chrome(options=options)

    s_date = start_date.replace(".", "")
    e_date = end_date.replace(".", "")
    url = f"https://search.naver.com/search.naver?where=news&query={keyword}&sort={sort}&ds={start_date}&de={end_date}&nso=so:dd,p:from{s_date}to{e_date},a:&start=1"

    print(f"[크롤링 시작] 키워드: {keyword}")
    print(f"[URL] {url}")

    driver.get(url)
    body = driver.find_element(By.TAG_NAME, "body")

    for i in range(max_scroll):
        body.send_keys(Keys.END)
        time.sleep(1.5)
        print(f"  [스크롤] {i+1}/{max_scroll}회 완료")

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # 📌 디버깅용 HTML 저장
    with open(f"{keyword}_page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
        print(f"[DEBUG] page_source 저장 완료 → {keyword}_page_source.html")

    driver.quit()

    titles, links, sources, dates, summaries, contents = [], [], [], [], [], []

    # 🔁 기존: news_area = soup.select("ul.list_news div.news_area")
    news_area = soup.select("div.sds-comps-full-layout.dlCcC3TMVQiSy85T_1b2")
    print(f"[DEBUG] 뉴스 영역 추출 결과 (new selector): {len(news_area)}건")

    for idx, news in enumerate(news_area):
        a_tag = news.select_one("a")
        if not a_tag or "href" not in a_tag.attrs:
            print(f"  [SKIP] 링크 없음 → idx={idx}")
            continue

        link = a_tag["href"]
        title_tag = a_tag.select_one("span.sds-comps-text-type-headline1")
        title = title_tag.get_text(strip=True) if title_tag else "[제목 없음]"

        print(f"  [기사 {idx+1}] {title} → {link}")

        source_tag = news.select_one("a.info.press")
        source = source_tag.get_text(strip=True) if source_tag else ""

        summary_tag = news.select_one("div.dsc_wrap")
        summary = summary_tag.get_text(strip=True) if summary_tag else ""

        date_tag = news.select_one("span.info")
        date = date_tag.get_text(strip=True) if date_tag else ""

        full_content = fetch_article_content(link)
        print(f"    ↳ 본문 길이: {len(full_content)}자")

        titles.append(title)
        links.append(link)
        sources.append(source)
        summaries.append(summary)
        dates.append(date)
        contents.append(full_content)

    if not titles:
        print(f"[WARN] '{keyword}' 키워드에 대해 수집된 결과가 없습니다.")
        return

    df = pd.DataFrame({
        "keyword": [keyword] * len(titles),
        "date": dates,
        "title": titles,
        "source": sources,
        "summary": summaries,
        "full_content": contents,
        "link": links
    })

    if os.path.exists(output_file):
        prev = pd.read_csv(output_file, encoding="utf-8-sig")
        df = pd.concat([prev, df], ignore_index=True)

    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"  ▶ '{keyword}' done, saved to {output_file} (총 {len(df)}건)")

# ───────────────────────────────────────────────────
# 5. 메인 실행 함수
# ───────────────────────────────────────────────────
# def main():
#     print("📰 네이버 뉴스 크롤링 시작")
#     max_scroll = int(input("스크롤 횟수 (예:5)> ").strip())
#     sort    = input("정렬 방식 (관련도=0, 최신=1, 오래된=2)> ").strip()
#     s_date  = input("시작일 YYYY.MM.DD> ").strip()
#     e_date  = input("종료일 YYYY.MM.DD> ").strip()
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M")

#     for stock in STOCKS:
#         name = stock["name"]
#         fname = f"{name}_{s_date.replace('.', '')}_{e_date.replace('.', '')}_{timestamp}.csv"
#         path  = os.path.join(RESULT_PATH, fname)
#         print(f"\n📌 [{name}] 뉴스 크롤링 시작 → 저장 경로: {path}")
#         for kw in stock["keywords"]:
#             print(f" - 키워드: {kw}")
#             crawler_with_scroll(kw, s_date, e_date, sort, path, max_scroll)

#     print("\n✅ 모든 작업이 완료되었습니다.")

# if __name__ == "__main__":
#     main()

def main():
    print("📰 네이버 뉴스 크롤링 시작")

    # ✅ 입력값 제거 & 테스트값 지정
    max_scroll = 4
    sort = "1"  # 최신순
    s_date = "2025.08.06"
    e_date = "2025.08.07"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    for stock in STOCKS:
        name = stock["name"]
        fname = f"{name}_{s_date.replace('.', '')}_{e_date.replace('.', '')}_{timestamp}.csv"
        path = os.path.join(RESULT_PATH, fname)
        print(f"\n📌 [{name}] 뉴스 크롤링 시작 → 저장 경로: {path}")
        for kw in stock["keywords"]:
            print(f" - 키워드: {kw}")
            crawler_with_scroll(kw, s_date, e_date, sort, path, max_scroll)

    print("\n✅ 모든 작업이 완료되었습니다.")

if __name__ == "__main__":
    main()