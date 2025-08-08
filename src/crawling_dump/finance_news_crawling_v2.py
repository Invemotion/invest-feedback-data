# # -*- coding: utf-8 -*-
# import requests
# from bs4 import BeautifulSoup
# from datetime import datetime
# import re
# import pandas as pd
# import os
# import time

# # ───────────────────────────────
# # 1. 설정 영역
# # ───────────────────────────────
# STOCKS = [
#     {"name": "삼성전자", "code": "005930"},
#     {"name": "NAVER",   "code": "035420"},
#     {"name": "카카오",   "code": "035720"},
#     {"name": "현대차",   "code": "005380"},
# ]
# START_DATE = "2025.08.01"
# END_DATE   = "2025.08.31"
# RESULT_DIR = "./"

# timestamp = datetime.now().strftime("%Y%m%d_%H%M")
# OUTPUT_FILE = os.path.join(
#     RESULT_DIR,
#     f"finance_news_{START_DATE.replace('.', '')}_{END_DATE.replace('.', '')}_{timestamp}.csv"
# )

# HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#         "AppleWebKit/537.36 (KHTML, like Gecko) "
#         "Chrome/114.0.0.0 Safari/537.36"
#     ),
#     "Referer": "https://finance.naver.com/",
#     "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
# }


# # ───────────────────────────────
# # 2. 본문 정제 함수
# # ───────────────────────────────
# def clean_text(html_fragment):
#     if html_fragment is None:
#         return ""
#     text = re.sub(r'<[^>]+>', '', str(html_fragment))
#     return text.strip()


# # ───────────────────────────────
# # 3. 상세 기사 본문 크롤러 (iframe 대응 포함)
# # ───────────────────────────────
# def fetch_article_content(link, session):
#     try:
#         art_resp = session.get(link)
#         art_resp.encoding = "euc-kr"
#         soup = BeautifulSoup(art_resp.text, "html.parser")

#         # ✅ iframe에서 실제 뉴스 페이지 추출
#         iframe = soup.find("iframe", id="news_read")
#         if iframe and iframe.get("src"):
#             iframe_url = iframe["src"]
#             if not iframe_url.startswith("http"):
#                 iframe_url = "https:" + iframe_url
#             print(f"    ↳ iframe 이동: {iframe_url}")

#             iframe_resp = session.get(iframe_url)
#             iframe_resp.encoding = "utf-8"
#             iframe_soup = BeautifulSoup(iframe_resp.text, "html.parser")

#             # ✅ 본문 추출 시도
#             body = (
#                 iframe_soup.select_one("#dic_area") or
#                 iframe_soup.select_one("#articleBodyContents") or
#                 iframe_soup.select_one("div#contents article")
#             )
#             return clean_text(body) if body else ""

#         # fallback: iframe 없을 경우 직접 파싱
#         body = (
#             soup.select_one("#dic_area") or
#             soup.select_one("#articleBodyContents") or
#             soup.select_one("div#contents article")
#         )
#         return clean_text(body) if body else ""
#     except Exception as e:
#         return f"[본문 파싱 실패: {e}]"


# # ───────────────────────────────
# # 4. 단일 종목 뉴스 크롤링
# # ───────────────────────────────
# def crawl_stock_news(stock_name, stock_code, start_date, end_date):
#     base_url = "https://finance.naver.com"
#     url_tpl = f"{base_url}/item/news_news.naver?code={stock_code}&page={{page}}&clusterId="

#     start_dt = datetime.strptime(start_date, "%Y.%m.%d").date()
#     end_dt   = datetime.strptime(end_date, "%Y.%m.%d").date()

#     session = requests.Session()
#     session.headers.update(HEADERS)

#     page = 1
#     collected = []

#     while True:
#         print(f"[{stock_name}] 페이지 {page}")
#         url = url_tpl.format(page=page)
#         resp = session.get(url)
#         resp.encoding = "euc-kr"
#         soup = BeautifulSoup(resp.text, "html.parser")

#         table = soup.find("table", attrs={"summary": "종목뉴스의 제목, 정보제공, 날짜"})
#         if not table:
#             print(" [경고] 뉴스 테이블 없음")
#             break

#         stop = False
#         for tr in table.select("tbody > tr"):
#             td_date = tr.find("td", class_="date")
#             if not td_date:
#                 continue
#             full_dt = td_date.get_text(strip=True)
#             date_only = full_dt.split()[0]
#             try:
#                 art_date = datetime.strptime(date_only, "%Y.%m.%d").date()
#             except ValueError:
#                 continue

#             if art_date < start_dt:
#                 stop = True
#                 break
#             if art_date > end_dt:
#                 continue

#             a_tag = tr.find("a", class_="tit")
#             info  = tr.find("td", class_="info")
#             if not a_tag or not info:
#                 continue

#             title  = a_tag.get_text(strip=True)
#             link   = a_tag["href"]
#             link   = link if link.startswith("http") else base_url + link
#             source = info.get_text(strip=True)

#             print(f"  [링크 이동] {link}")  


#             content = fetch_article_content(link, session)
#             if content.strip():
#                 print(f"  [본문 수집] {title[:30]} → {content[:80]}...")
#             else:
#                 print(f"  [본문 없음] {title[:30]}")

#             time.sleep(0.2)

#             collected.append({
#                 "stock_name": stock_name,
#                 "date": date_only,
#                 "title": title,
#                 "source": source,
#                 "content": content,
#                 "link": link,
#             })

#         if stop:
#             break

#         next_btn = soup.select_one("td.pgR > a")
#         if next_btn:
#             page += 1
#             time.sleep(0.3)
#         else:
#             break

#     return collected


# # ───────────────────────────────
# # 5. 전체 종목 순회 및 저장
# # ───────────────────────────────
# def main():
#     os.makedirs(RESULT_DIR, exist_ok=True)
#     all_results = []

#     for stock in STOCKS:
#         print(f"[크롤링 시작] {stock['name']}({stock['code']})")
#         data = crawl_stock_news(stock["name"], stock["code"], START_DATE, END_DATE)
#         print(f" [완료] {len(data)}건 수집")
#         all_results.extend(data)

#     df = pd.DataFrame(all_results)
#     if df.empty:
#         print("[INFO] 수집된 데이터가 없습니다.")
#         return

#     df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
#     print(f"[저장 완료] {OUTPUT_FILE}")


# # ───────────────────────────────
# # 6. 실행
# # ───────────────────────────────
# if __name__ == "__main__":
#     main()

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
# 3. 상세 기사 본문 크롤러 개선
# ───────────────────────────────
def fetch_article_content(link, session):
    try:
        resp = session.get(link)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, "html.parser")
        # 다양한 컨테이너 시도
        selectors = [
            "#articleBodyContents",
            "div#contents div.newsct_body",
            "article#dic_area",
            "div.newsct_body"
        ]
        for sel in selectors:
            body = soup.select_one(sel)
            if body:
                print(f"    ↳ 본문 컨테이너 발견: {sel}")
                return clean_text(body)
        # fallback 전체 본문
        return clean_text(soup)
    except Exception as e:
        print(f"    ↳ 본문 에러: {e}")
        return ""

# ───────────────────────────────
# 4. 단일 종목 뉴스 크롤링
# ───────────────────────────────
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