# Google News RSS Scraper

Google News RSS 피드를 기반으로 뉴스 기사를 수집하고, 본문을 스크래핑하여 PostgreSQL DB와 JSON 파일로 저장하는 도구입니다.

## 주요 기능

- **키워드 기반 뉴스 검색**: Google News RSS를 통해 키워드별 최신 뉴스 수집
- **스마트 본문 추출**: BeautifulSoup + LLM(Ollama) 하이브리드 방식으로 안정적인 본문 추출
- **이중 저장**: PostgreSQL DB + 개별 JSON 파일로 데이터 저장
- **날짜 기반 검색**: 특정 기간의 뉴스만 수집 가능
- **자동 중복 제거**: Google News 링크 기반으로 중복 기사 자동 필터링

## 시스템 요구사항

- Python 3.8+
- PostgreSQL 12+
- Ollama (선택사항, LLM 기반 본문 추출용)

## 설치

1. **저장소 클론**
```bash
git clone <repository-url>
cd g_data
```

2. **Python 패키지 설치**
```bash
pip install -r requirements.txt
```

필요한 패키지:
- feedparser
- requests
- beautifulsoup4
- lxml
- psycopg2-binary
- python-dotenv
- googlenewsdecoder

3. **PostgreSQL 데이터베이스 설정**

```sql
CREATE DATABASE news;

CREATE TABLE news_articles (
    id           BIGSERIAL PRIMARY KEY,
    keyword      TEXT NOT NULL,
    title        TEXT NOT NULL,
    link         TEXT,
    google_link  TEXT NOT NULL UNIQUE,
    published_at TIMESTAMPTZ,
    source_name  TEXT,
    body_path    TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 사용자 생성 및 권한 부여
CREATE USER app_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON TABLE news_articles TO app_user;
GRANT ALL PRIVILEGES ON SEQUENCE news_articles_id_seq TO app_user;
```

4. **환경 변수 설정**

`.env` 파일 생성:
```bash
# PostgreSQL Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=news
DB_USER=news_app_user
DB_PASSWORD=your_password

# LLM settings (optional)
LLM_ENABLED=true
LLM_API_BASE=http://localhost:11434
LLM_MODEL=qwen3:latest
LLM_TIMEOUT=60
```

5. **Ollama 설치 (선택사항)**

LLM 기반 본문 추출을 사용하려면:
```bash
# Ollama 설치
curl -fsSL https://ollama.com/install.sh | sh

# qwen3 모델 다운로드
ollama pull qwen3:latest

# Ollama 서버 실행
ollama serve
```

LLM을 사용하지 않으려면 `.env`에서:
```bash
LLM_ENABLED=false
```

## 사용법

### 기본 사용

```bash
# 단일 키워드로 뉴스 수집
python main.py --keywords tesla

# 여러 키워드로 수집
python main.py --keywords tesla apple google

# 수집 개수 제한 (키워드당 최대 10개)
python main.py --keywords tesla --max-articles 10

# 날짜 범위 지정
python main.py --keywords tesla --d-after 2026-03-01 --d-before 2026-03-10
```

### 명령어 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--keywords` | 검색할 키워드 (공백으로 구분) | 없음 (필수) |
| `--max-articles` | 키워드당 최대 수집 개수 | 제한 없음 |
| `--d-after` | 시작 날짜 (YYYY-MM-DD) | 없음 |
| `--d-before` | 종료 날짜 (YYYY-MM-DD) | 없음 |

### 사용 예시

```bash
# 최근 뉴스 전체 수집
python main.py --keywords "artificial intelligence" AI

# 특정 기간의 테슬라 뉴스 수집
python main.py --keywords tesla --d-after 2026-03-01 --d-before 2026-03-15

# 빠른 테스트 (각 키워드당 2개만)
python main.py --keywords apple tesla --max-articles 2
```

## 데이터 저장 구조

### 1. PostgreSQL 데이터베이스
- 테이블: `news_articles`
- 메타데이터 저장 (제목, 링크, 발행일, 출처 등)
- `body_path`: JSON 파일 경로 참조

### 2. JSON 파일
- 경로: `/data/news/YYYY/MM/DD/[source_name]_title.json`
- 파일명 예시: `[Reuters]_Tesla_announces_new_model.json`
- 내용:
```json
{
  "title": "기사 제목",
  "link": "실제 뉴스 URL",
  "google_link": "Google News RSS URL",
  "published_at": "2026-03-12T10:30:00+00:00",
  "source_name": "Reuters",
  "body": "기사 본문 전체 내용...",
  "created_at": "2026-03-12T12:00:00+00:00"
}
```

## 아키텍처

```
1. RSS Fetcher (src/rss_fetcher.py)
   ↓ Google News RSS 피드 수집

2. URL Resolver (src/data_processor.py)
   ↓ Google News 리다이렉트 URL → 실제 뉴스 URL 변환

3. Web Scraper (src/scraper.py)
   ↓ BeautifulSoup으로 본문 추출 시도
   ↓ (실패 시)
   ↓ LLM(Ollama)으로 본문 추출

4. Data Processor (src/data_processor.py)
   ↓ 데이터 정제 및 저장
   ├─→ JSON 파일 저장 (/data/news/YYYY/MM/DD/)
   └─→ PostgreSQL DB 저장
```

## 주요 특징

### 하이브리드 스크래핑
- **1차 시도**: BeautifulSoup으로 HTML 파싱 (빠름)
- **2차 시도**: LLM으로 본문 추출 (정확함)
- **자동 필터링**: LLM이 잘못된 응답(corrupted, binary 등)을 반환하면 자동으로 제외

### 타임존 관리
- 모든 시간은 **UTC**로 통일 저장
- DB의 `published_at`, `created_at` 모두 UTC timestamptz
- 필요시 애플리케이션 레벨에서 KST(UTC+9) 등으로 변환

### 중복 제거
- Google News 링크(`google_link`)를 unique key로 사용
- 동일한 기사가 여러 키워드로 검색되어도 한 번만 저장

## 프로젝트 구조

```
g_data/
├── config/
│   └── config.py          # 설정 관리
├── src/
│   ├── rss_fetcher.py     # RSS 피드 수집
│   ├── scraper.py         # 웹 스크래핑
│   ├── data_processor.py  # 데이터 처리 및 저장
│   └── utils.py           # 유틸리티 함수
├── test/
│   └── test_*.py          # 테스트 스크립트
├── logs/                  # 로그 파일
├── main.py               # 메인 실행 스크립트
├── .env                  # 환경 변수 (git 제외)
├── .env.example          # 환경 변수 예시
└── README.md
```

## 문제 해결

### Ollama 404 에러
```bash
# Ollama 실행 확인
ollama list

# 모델명 확인 (qwen3:latest 또는 qwen3:8b)
# .env 파일에서 LLM_MODEL 수정
```

### PostgreSQL 권한 에러
```sql
-- 시퀀스 권한 부여
GRANT USAGE, SELECT ON SEQUENCE news_articles_id_seq TO news_app_user;
GRANT ALL PRIVILEGES ON TABLE news_articles TO news_app_user;
```

### 본문 추출 실패
- LLM을 활성화하면 성공률이 높아집니다
- 일부 사이트(Bloomberg, WSJ 등)는 paywall로 접근이 제한됩니다

## 라이센스

MIT License

## 기여

이슈나 풀 리퀘스트는 언제나 환영합니다!
