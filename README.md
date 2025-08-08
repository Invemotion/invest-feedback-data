# invest-feedback-data

한국투자증권 Open API를 활용하여 투자 성향 기반 더미 매매 기록과 복기 일지 데이터를 생성
AI 기반 투자 복기 시스템의 데이터 수집 및 전처리, 더미 데이터 생성, 뉴스 기반 인사이트 확보에 사용

---

## 주요 기능

* **30일간 주식 시세 데이터 수집** (`fetch_price_historical.py`)
* **투자 성향별 매수/매도 더미 매매 기록 생성** (`generate_trade_history_from_prices.py`)
* **매매 복기용 더미 일지 생성** (`generate_trade_journals.py`)
* **종목별 뉴스 기사 제목·본문 크롤링** (`finance_news_crawling_v3.1.py`)

  * 네이버 금융 뉴스 페이지 기반
  * 본문 크롤링 포함 (`redirect`, `본문 selector` 대응 포함)
  * CSV로 저장 (종목명, 날짜, 제목, 출처, 본문, 링크)

---

## 설치 및 실행

```bash
# Python 3.8 이상 권장
pip install -r requirements.txt  # 필요시

# ① 시세 데이터 수집
python fetch_price_historical.py

# ② 더미 매매 기록 생성
python generate_trade_history_from_prices.py

# ③ 매매 일지 더미 생성
python generate_trade_journals.py

# ④ 종목별 뉴스 크롤링 실행
python finance_news_crawling_v3.1.py
```

---

## 파일 구조

```
project/
├── data/                              # 데이터 저장용 폴더
│   ├── historical_prices.json         # 시세 데이터
│   ├── dummy_trade_history.json       # 더미 매매 기록
│   └── dummy_trade_journals.json      # 더미 매매 일지
├── results/                           # 크롤링한 뉴스 데이터 CSV 저장 폴더
│   └── 삼성전자_20250807_1510.csv 등
├── src/                               # 소스 코드
│   ├── fetch_price_historical.py
│   ├── generate_trade_history_from_prices.py
│   ├── generate_trade_journals.py
│   ├── finance_news_crawling_v3.1.py  # 종목 뉴스 크롤링
│   └── kis_auth.py                    # 인증 정보 (gitignore 대상)
├── .gitignore
└── README.md
```
