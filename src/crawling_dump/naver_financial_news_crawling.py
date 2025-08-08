# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
import pandas as pd
import time
import os
import re
import requests

# ───────────────────────────────────────────────────
# 설정
# ───────────────────────────────────────────────────
STOCKS = [
    {"name": "삼성전자", "keywords": ["삼성전자"]},
    {"name": "NAVER", "keywords": ["NAVER"]},
    {"name": "카카오", "keywords": ["카카오"]},
    {"name": "현대차", "keywords": ["현대차"]},
]

RESULT_PATH = './results'
os.makedirs(RESULT_PATH, exist_ok=True)

# ───────────────────────────────────────────────────
# 도메인별 본문 selector
# ───────────────────────────────────────────────────
DOMAIN_SELECTORS = {
    "news.naver.com": ["#dic_area", "#articleBodyContents"],
    "etnews.com": ["div.article_txt"],
    "hankooki.com": ["#article-view-content-div"],
    "joongangenews.com": ["#article-view-content-div"],
    "wowtv.co.kr": ["div.view-cont"],
    # 필요한 언론사 계속 추가
}

# ───────────────────────────────────────────────────
# 본문 정제 함수
# ───────────────────────────────────────────────────
def clean_text(html_fragment):
    if not html_fragment:
        return ""
    text = re.sub(r'<[^>]+>', '', str(html_fragment))
    return text.strip()

# ───────────────────────────────────────────────────
# 본문 크롤링 함수
# ───────────────────────────────────────────────────
def fetch_article_content(url):
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        domain = urlparse(url).netloc.replace('www.', '')
        selectors = DOMAIN_SELECTORS.get(domain, [])

        for sel in selectors:
            node = soup.select_one(sel)
            if node:
                print(f"    ↳ 본문 selector '{sel}' 성공 (by domain)")
                return clean_text(node)

        fallback_selectors = ["#dic_area", "#articleBodyContents", "div#contents .newsct_body", "article#dic_area"]
        for sel in fallback_selectors:
            node = soup.select_one(sel)
            if node:
                print(f"    ↳ 본문 selector '{sel}' 성공 (fallback)")
                return clean_text(node)

        print("    ↳ 본문 추출 실패")
        return ""
    except Exception as e:
        print(f"    ↳ 본문 오류: {e}")
        return ""

# ───────────────────────────────────────────────────
# 뉴스 수집 함수
# ───────────────────────────────────────────────────
def crawler_with_scroll(keyword, start_date, end_date, sort, output_file, max_scroll=5):
    options = Options()
    options.add_argument('--disable-gpu')
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
    with open(f"{keyword}_page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    driver.quit()

    news_area = soup.select("div.sds-comps-full-layout.dlCcC3TMVQiSy85T_1b2")
    print(f"[DEBUG] 뉴스 영역 추출 결과 (new selector): {len(news_area)}건")

    titles, links, sources, dates, summaries, contents = [], [], [], [], [], []

    for idx, news in enumerate(news_area):
        a_tag = news.select_one("a")
        if not a_tag or "href" not in a_tag.attrs:
            continue

        link = a_tag["href"]
        title_tag = a_tag.select_one("span.sds-comps-text-type-headline1")
        title = title_tag.get_text(strip=True) if title_tag else "[제목 없음]"

        print(f"  [기사 {idx+1}] {title} → {link}")

        full_content = fetch_article_content(link)
        print(f"    ↳ 본문 길이: {len(full_content)}자")

        titles.append(title)
        links.append(link)
        sources.append("")
        summaries.append("")
        dates.append("")
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
# 메인 실행 함수
# ───────────────────────────────────────────────────
def main():
    print("📰 네이버 뉴스 크롤링 시작")

    # 입력 제거 & 테스트용 기본값 지정
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