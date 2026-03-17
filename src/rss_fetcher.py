"""
Google News RSS Feed Fetcher
"""
import feedparser
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
from config.config import Config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RSSFetcher:
    """Google News RSS Feed 데이터 수집 클래스"""

    def __init__(self, config: Config = None):
        """
        Initialize RSS Fetcher

        Args:
            config: Configuration object
        """
        self.config = config or Config()

    def fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch RSS feed from URL

        Args:
            url: RSS feed URL

        Returns:
            Parsed feed object or None if failed
        """
        try:
            logger.info(f"Fetching RSS feed from: {url}")
            feed = feedparser.parse(url)

            if feed.bozo:
                logger.warning(f"Feed parsing warning: {feed.bozo_exception}")

            logger.info(f"Successfully fetched {len(feed.entries)} entries")
            return feed

        except Exception as e:
            logger.error(f"Error fetching RSS feed: {e}")
            return None

    def fetch_by_keyword(self, keyword: str, d_after: str = None, d_before: str = None) -> Optional[feedparser.FeedParserDict]:
        """
        Fetch Google News RSS by keyword

        Args:
            keyword: Search keyword
            d_after: base date for search '2026-03-01' (optional)
            d_before: end date for search '2026-03-08' (optional)

        Returns:
            Parsed feed object
        """
        url = self.config.get_google_news_url(keyword=keyword, d_after=d_after, d_before=d_before)
        return self.fetch_feed(url)

    def parse_entries(self, feed: feedparser.FeedParserDict) -> List[Dict]:
        """
        Parse feed entries into structured data

        Args:
            feed: Parsed feed object

        Returns:
            List of article dictionaries
        """
        articles = []
        for entry in feed.entries:
            try:
                article = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'published_parsed': self._parse_date(entry.get('published_parsed')),
                    'summary': entry.get('summary', ''),
                    'source': entry.get('source', {}).get('title', ''),
                    'fetched_at': datetime.now(timezone.utc).isoformat()
                }
                articles.append(article)

            except Exception as e:
                logger.error(f"Error parsing entry: {e}")
                continue

        return articles

    def _parse_date(self, date_tuple) -> Optional[str]:
        """
        Parse date tuple to ISO format string (UTC)

        Args:
            date_tuple: Time tuple from feedparser

        Returns:
            ISO format date string (UTC) or None
        """
        try:
            if date_tuple:
                # RSS feed dates are typically in UTC
                dt = datetime(*date_tuple[:6], tzinfo=timezone.utc)
                return dt.isoformat()
        except Exception as e:
            logger.error(f"Error parsing date: {e}")

        return None

    def fetch_multiple_keywords(self, keywords: List[str], d_after: str = None, d_before: str = None) -> Dict[str, List[Dict]]:
        """
        Fetch RSS feeds for multiple keywords

        Args:
            keywords: List of search keywords
            d_after: base date for search '2026-03-01' (optional)
            d_before: end date for search '2026-03-09' (optional)

        Returns:
            Dictionary mapping keywords to article lists
        """
        results = {}

        for keyword in keywords:
            logger.info(f"Fetching articles for keyword: {keyword}")
            feed = self.fetch_by_keyword(keyword, d_after=d_after, d_before=d_before)

            if feed:
                articles = self.parse_entries(feed)
                # Add keyword to each article
                for article in articles:
                    article['keyword'] = keyword
                results[keyword] = articles
                logger.info(f"Found {len(articles)} articles for '{keyword}'")
            else:
                results[keyword] = []
                logger.warning(f"No articles found for '{keyword}'")

        return results


# Example usage
if __name__ == "__main__":
    # Initialize fetcher
    fetcher = RSSFetcher()

    # Fetch by keyword
    feed = fetcher.fetch_by_keyword("tesla", d_after='2026-01-01')
    if feed:
        articles = fetcher.parse_entries(feed)
        print(f"Found {len(articles)} articles")
        for article in articles:
            print(f"\nTitle: {article['title']}")
            print(f"Link: {article['link']}")
            print(f"Published: {article['published']}")
        print(len(articles))
        print(article['published'], type(article['published']))
    #
    # # Fetch multiple keywords
    # keywords = ["파이썬", "데이터분석", "머신러닝"]
    # results = fetcher.fetch_multiple_keywords(keywords)
    # for keyword, articles in results.items():
    #     print(f"\n{keyword}: {len(articles)} articles")
