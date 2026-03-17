"""
Configuration module for Google News RSS scraper
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# https://news.google.com/search?q=tesla%20when%3A365d&hl=en-US&gl=US&ceid=US
class Config:
    """Application configuration"""

    # Project root directory
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Data directories
    DATA_DIR = Path("/data/news")
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
    LOG_DIR = BASE_DIR / "logs"

    # Google News RSS base URL
    GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss"

    # Default search keywords for Google News
    DEFAULT_KEYWORDS = [
        "technology",
        "AI",
        "python",
        "데이터분석",
    ]

    # RSS feed settings
    RSS_LANGUAGE = "en-US"  # Language code (ko, en, etc.)
    RSS_COUNTRY = "US"   # Country code (KR, US, etc.)

    # Scraping settings
    REQUEST_TIMEOUT = 10  # seconds
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    # Data processing settings
    MAX_ARTICLES_PER_KEYWORD = 50
    SAVE_FORMAT = "json"  # json or csv

    # Database settings (PostgreSQL)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "google_news")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # LLM settings for content extraction
    LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
    LLM_API_BASE = os.getenv("LLM_API_BASE", "http://localhost:11434")  # Ollama default
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:8b")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist"""
        for directory in [cls.DATA_DIR, cls.RAW_DATA_DIR,
                         cls.PROCESSED_DATA_DIR, cls.LOG_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_google_news_url(cls, keyword=None, topic=None, d_after=None, d_before=None):
        """
        Generate Google News RSS URL

        Args:
            keyword: Search keyword
            topic: Topic category (WORLD, NATION, BUSINESS, TECHNOLOGY, etc.)
            d_after: base date for search '2026-03-01'
            d_before: end date for search '2026-03-08'

        Returns:
            RSS URL string
        """
        from datetime import datetime, timedelta

        # Handle date range logic
        date_query = ""
        if d_after is not None or d_before is not None:
            # If only one date is provided, create 7-day range
            if d_after is None:
                # d_before is provided, calculate d_after as 7 days before
                before_date = datetime.strptime(d_before, '%Y-%m-%d')
                after_date = before_date - timedelta(days=7)
                d_after = after_date.strftime('%Y-%m-%d')
            elif d_before is None:
                # d_after is provided, calculate d_before as 7 days after
                after_date = datetime.strptime(d_after, '%Y-%m-%d')
                before_date = after_date + timedelta(days=7)
                d_before = before_date.strftime('%Y-%m-%d')

            # Build date query string
            date_query = f"+after:{d_after}+before:{d_before}"

        if keyword:
            # Search by keyword with optional date range
            return f"{cls.GOOGLE_NEWS_RSS_BASE}/search?q={keyword}{date_query}&hl={cls.RSS_LANGUAGE}&gl={cls.RSS_COUNTRY}&ceid={cls.RSS_COUNTRY}:{cls.RSS_LANGUAGE}"
        elif topic:
            # Search by topic
            return f"{cls.GOOGLE_NEWS_RSS_BASE}/topics/{topic}?hl={cls.RSS_LANGUAGE}&gl={cls.RSS_COUNTRY}&ceid={cls.RSS_COUNTRY}:{cls.RSS_LANGUAGE}"
        else:
            # Top stories
            return f"{cls.GOOGLE_NEWS_RSS_BASE}?hl={cls.RSS_LANGUAGE}&gl={cls.RSS_COUNTRY}&ceid={cls.RSS_COUNTRY}:{cls.RSS_LANGUAGE}"
