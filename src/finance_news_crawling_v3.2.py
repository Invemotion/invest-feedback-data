# 뉴스 "날짜 시간:분" 가져오도록 수정
# TARGET_DATE 지정 -> 2025.08.05

# -*- coding: utf-8 -*-
import requests, re, os, time, csv
from bs4 import BeautifulSoup
from datetime import datetime

# ───────────────────────────────
# 1. 설정 영역
# ───────────────────────────────
STOCKS      = [
    {"name": "삼성전자", "code": "005930"},
    {"name": "NAVER",   "code": "035420"},
    {"name": "카카오",   "code": "035720"},
    {"name": "현대차",   "code": "005380"},
]
MAX_PAGES   = 200
RESULT_DIR  = "./results"
timestamp   = datetime.now().strftime("%Y%m%d_%H%M")

TARGET_DATE = "2025.08.05"        # ← 크롤링을 제한할 ‘날짜’(연‧월‧일)

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
# 2. 본문 정제 & 기사 본문 수집
# ───────────────────────────────
def clean_text(html_fragment):
    return re.sub(r'<[^>]+>', '', str(html_fragment)).strip() if html_fragment else ""

def fetch_article_content(link, session, depth=0):
    if depth > 2:
        return ""
    try:
        resp = session.get(link); resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        # JS redirect 대응
        redirect = soup.find("script", text=re.compile(r"top\.location\.href"))
        if redirect:
            m = re.search(r"top\.location\.href\s*=\s*'([^']+)';", redirect.string)
            if m:
                return fetch_article_content(m.group(1), session, depth+1)

        for sel in ("#articleBodyContents",
                    "div#contents .newsct_body",
                    "article#dic_area",
                    "div.newsct_body"):
            body = soup.select_one(sel)
            if body:
                return clean_text(body)
        return clean_text(soup)
    except Exception:
        return ""

# ───────────────────────────────
# 3. 종목별 뉴스 크롤링
# ───────────────────────────────
def crawl_stock_news(stock_name, stock_code, csv_writer):
    base_url = "https://finance.naver.com"
    url_tpl  = f"{base_url}/item/news_news.naver?code={stock_code}&page={{page}}&clusterId="

    target_dt = datetime.strptime(TARGET_DATE, "%Y.%m.%d")
    session   = requests.Session(); session.headers.update(HEADERS)
    visited   = set()

    for page in range(1, MAX_PAGES + 1):
        resp = session.get(url_tpl.format(page=page)); resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = soup.select('table[summary="종목뉴스의 제목, 정보제공, 날짜"] tbody > tr')
        if not rows:
            break

        for tr in rows:
            td_date = tr.find("td", class_="date")
            if not td_date:
                continue

            # ‘날짜 + 시:분’ 문자열 → 날짜·시간 분리
            date_time = " ".join(td_date.stripped_strings)
            date_part = date_time.split()[0]            # YYYY.MM.DD

            # ── 날짜 필터 ────────────────────────────────
            row_dt = datetime.strptime(date_part, "%Y.%m.%d")
            if row_dt < target_dt:
                return                               # 더 오래된 페이지로 갈수록 날짜가 작아지므로 종료
            if row_dt > target_dt:
                continue                             # 8/5보다 최신 글이면 패스하고 다음 행

            a_tag = tr.find("a", class_="tit")
            info  = tr.find("td", class_="info")
            if not a_tag or not info:
                continue

            href  = a_tag["href"]
            m_id  = re.search(r"article_id=(\d+).+office_id=(\d+)", href)
            if m_id:
                key = f"{m_id.group(2)}_{m_id.group(1)}"
                if key in visited:
                    continue
                visited.add(key)

            title   = a_tag.get_text(strip=True)
            link    = href if href.startswith("http") else base_url + href
            source  = info.get_text(strip=True)
            content = fetch_article_content(link, session)
            time.sleep(0.2)

            csv_writer.writerow([
                stock_name,
                date_time,
                title,
                source,
                content,
                link,
            ])

# ───────────────────────────────
# 4. 메인 실행
# ───────────────────────────────
def main():
    os.makedirs(RESULT_DIR, exist_ok=True)
    for stock in STOCKS:
        path = os.path.join(RESULT_DIR, f"{stock['name']}_{timestamp}.csv")
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["stock_name", "datetime", "title", "source", "content", "link"])
            crawl_stock_news(stock["name"], stock["code"], writer)
        print(f"[완료] {stock['name']} 저장")

if __name__ == "__main__":
    main()
