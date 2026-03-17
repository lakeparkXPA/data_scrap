"""
Data processing and storage module
"""
import json
import logging
import requests
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
from config.config import Config
from googlenewsdecoder import new_decoderv1


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataProcessor:
    """데이터 처리 및 저장 클래스"""

    def __init__(self, config: Config = None):
        """
        Initialize Data Processor

        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.config.ensure_directories()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.USER_AGENT
        })
        self.db_conn = None

    def _get_db_connection(self):
        """Get PostgreSQL database connection"""
        if self.db_conn is None or self.db_conn.closed:
            try:
                self.db_conn = psycopg2.connect(
                    host=self.config.DB_HOST,
                    port=self.config.DB_PORT,
                    database=self.config.DB_NAME,
                    user=self.config.DB_USER,
                    password=self.config.DB_PASSWORD
                )
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise
        return self.db_conn

    def resolve_google_news_url(self, url: str) -> Optional[str]:
        """
        Resolve Google News redirect URL to actual article URL using googlenewsdecoder

        Args:
            url: Google News redirect URL

        Returns:
            Final redirected URL or original URL if failed
        """
        # Check if it's a Google News redirect URL
        if 'news.google.com' not in url:
            return url

        try:
            # Use googlenewsdecoder to decode the URL
            decoded_url = new_decoderv1(url, interval=1)

            # Handle case where decoded_url might be a dict or other type
            if isinstance(decoded_url, dict):
                decoded_url = decoded_url.get('decoded_url', url)

            # Ensure decoded_url is a string
            if decoded_url and isinstance(decoded_url, str) and decoded_url != url:
                logger.info(f"Resolved: {url[:50]}... -> {decoded_url[:80]}...")
                return decoded_url
            else:
                logger.warning(f"Could not decode URL: {url[:80]}...")
                return url

        except Exception as e:
            logger.warning(f"Failed to resolve redirect URL: {e}")
            return url  # Return original URL if resolution fails

    def resolve_urls(self, articles: List[Dict]) -> List[Dict]:
        """
        Resolve all Google News redirect URLs in articles

        Args:
            articles: List of article dictionaries with 'link' field

        Returns:
            Articles with resolved URLs
        """
        resolved_articles = []

        for article in articles:
            resolved_article = article.copy()
            original_url = article.get('link', '')

            if original_url:
                final_url = self.resolve_google_news_url(original_url)
                resolved_article['link'] = final_url
                resolved_article['google_link'] = original_url

            resolved_articles.append(resolved_article)

        logger.info(f"Resolved {len(resolved_articles)} URLs")
        return resolved_articles

    def save_article_json(self, article: Dict) -> Optional[str]:
        """
        Save individual article to JSON file with date-based directory structure

        Args:
            article: Article dictionary with title, link, google_link, published_at, source_name, body, created_at

        Returns:
            Relative path to saved file (from data/news) or None if failed
        """
        try:
            # Parse published_at to determine directory (always use UTC)
            published_at = article.get('published_at')
            if published_at:
                if isinstance(published_at, str):
                    try:
                        published_dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        # Ensure timezone-aware and convert to UTC
                        if published_dt.tzinfo is None:
                            published_dt = published_dt.replace(tzinfo=timezone.utc)
                        else:
                            published_dt = published_dt.astimezone(timezone.utc)
                    except:
                        published_dt = datetime.now(timezone.utc)
                else:
                    # If datetime object, ensure it's UTC
                    if published_at.tzinfo is None:
                        published_dt = published_at.replace(tzinfo=timezone.utc)
                    else:
                        published_dt = published_at.astimezone(timezone.utc)
            else:
                published_dt = datetime.now(timezone.utc)

            # Create date-based directory path: data/news/YYYY/MM/DD
            date_dir = self.config.DATA_DIR / 'news' / str(published_dt.year) / f"{published_dt.month:02d}" / f"{published_dt.day:02d}"
            date_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename: [source_name]_title.json (remove spaces)
            source_name = article.get('source_name', 'unknown').replace(' ', '_')
            title = article.get('title', 'untitled')[:50].replace(' ', '_')  # Limit title length
            # Remove special characters that might cause file system issues
            import re
            source_name = re.sub(r'[<>:"/\\|?*]', '', source_name)
            title = re.sub(r'[<>:"/\\|?*]', '', title)

            # Use brackets to distinguish source from title
            filename = f"[{source_name}]_{title}.json"
            filepath = date_dir / filename

            # Prepare JSON content
            json_content = {
                'title': article.get('title', ''),
                'link': article.get('link', ''),
                'google_link': article.get('google_link', ''),
                'published_at': published_dt.isoformat() if published_dt else None,
                'source_name': article.get('source_name', ''),
                'body': article.get('body', ''),
                'created_at': datetime.now(timezone.utc).isoformat()
            }

            # Save JSON file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_content, f, ensure_ascii=False, indent=2)

            # Return relative path from data/news directory
            relative_path = filepath.relative_to(self.config.DATA_DIR / 'news')
            logger.info(f"Saved article JSON to {filepath}")
            return str(relative_path)

        except Exception as e:
            logger.error(f"Error saving article JSON: {e}")
            return None

    def save_to_json(self, data: List[Dict], filename: str, directory: Path = None) -> str:
        """
        Save data to JSON file

        Args:
            data: List of dictionaries to save
            filename: Output filename
            directory: Target directory (default: RAW_DATA_DIR)

        Returns:
            Path to saved file
        """
        try:
            if directory is None:
                directory = self.config.RAW_DATA_DIR

            # Add timestamp to filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{timestamp}.json"
            filepath = directory / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Data saved to {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"Error saving JSON: {e}")
            raise

    def save_to_db(self, data: List[Dict]) -> int:
        """
        Save data to PostgreSQL database

        Args:
            data: List of article dictionaries

        Returns:
            Number of records inserted/updated
        """
        if not data:
            logger.warning("No data to save to database")
            return 0

        try:
            conn = self._get_db_connection()

            # Prepare insert query with ON CONFLICT for upsert
            insert_query = """
            INSERT INTO news_articles
            (keyword, title, link, google_link, published_at, source_name, body_path)
            VALUES %s
            ON CONFLICT (google_link)
            DO UPDATE SET
                keyword = EXCLUDED.keyword,
                title = EXCLUDED.title,
                link = EXCLUDED.link,
                published_at = EXCLUDED.published_at,
                source_name = EXCLUDED.source_name,
                body_path = EXCLUDED.body_path
            """

            # Prepare data tuples
            values = []
            for article in data:
                # Parse published date (always use UTC)
                published_at = article.get('published_parsed') or article.get('published')
                if published_at and isinstance(published_at, str):
                    try:
                        published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        # Ensure timezone-aware and convert to UTC
                        if published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                        else:
                            published_at = published_at.astimezone(timezone.utc)
                    except:
                        published_at = None

                values.append((
                    article.get('keyword', ''),
                    article.get('title', ''),
                    article.get('link', ''),
                    article.get('google_link', ''),
                    published_at,
                    article.get('source', ''),
                    article.get('body_path', None)
                ))

            # Execute batch insert
            with conn.cursor() as cursor:
                execute_values(cursor, insert_query, values)
                conn.commit()
                inserted_count = cursor.rowcount

            logger.info(f"Saved {inserted_count} articles to database")
            return inserted_count

        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            if conn:
                conn.rollback()
            raise

    def load_json(self, filepath: str) -> List[Dict]:
        """
        Load data from JSON file

        Args:
            filepath: Path to JSON file

        Returns:
            List of dictionaries
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded {len(data)} records from {filepath}")
            return data

        except Exception as e:
            logger.error(f"Error loading JSON: {e}")
            raise

    def close_connection(self):
        """Close database connection"""
        if self.db_conn and not self.db_conn.closed:
            self.db_conn.close()
            logger.info("Database connection closed")

    def __del__(self):
        """Destructor to ensure connection is closed"""
        self.close_connection()

    def remove_duplicates(self, data: List[Dict], key: str = 'link') -> List[Dict]:
        """
        Remove duplicate entries based on key

        Args:
            data: List of dictionaries
            key: Key to check for duplicates

        Returns:
            List with duplicates removed
        """
        seen = set()
        unique_data = []

        for item in data:
            value = item.get(key)
            if value and value not in seen:
                seen.add(value)
                unique_data.append(item)

        removed = len(data) - len(unique_data)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate entries")

        return unique_data

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Remove special characters if needed
        # text = re.sub(r'[^\w\s가-힣]', '', text)

        return text.strip()

    def process_articles(self, articles: List[Dict], save_json: bool = True) -> List[Dict]:
        """
        Process and clean article data, optionally save to JSON files

        Args:
            articles: List of article dictionaries
            save_json: Whether to save individual JSON files

        Returns:
            Processed article list with body_path filled
        """
        processed = []

        for article in articles:
            try:
                # Parse published date (always use UTC)
                published = article.get('published_parsed') or article.get('published')
                if published and isinstance(published, str):
                    try:
                        published_dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
                        # Ensure timezone-aware and convert to UTC
                        if published_dt.tzinfo is None:
                            published_dt = published_dt.replace(tzinfo=timezone.utc)
                        else:
                            published_dt = published_dt.astimezone(timezone.utc)
                    except:
                        published_dt = None
                elif published:
                    # If datetime object, ensure it's UTC
                    if hasattr(published, 'tzinfo'):
                        if published.tzinfo is None:
                            published_dt = published.replace(tzinfo=timezone.utc)
                        else:
                            published_dt = published.astimezone(timezone.utc)
                    else:
                        published_dt = published
                else:
                    published_dt = None

                # Prepare article for JSON saving
                article_for_json = {
                    'title': self.clean_text(article.get('title', '')),
                    'link': article.get('link', ''),
                    'google_link': article.get('google_link', ''),
                    'published_at': published_dt.isoformat() if published_dt else None,
                    'source_name': article.get('source', ''),
                    'body': article.get('body', ''),
                }

                # Save JSON and get body_path (only if body is not empty)
                body_path = None
                body_content = article_for_json.get('body', '').strip()
                if save_json:
                    if body_content:
                        body_path = self.save_article_json(article_for_json)
                    else:
                        logger.warning(f"Skipping JSON save for article (empty body): {article_for_json.get('title', 'Unknown')[:50]}... (URL: {article_for_json.get('link', 'N/A')[:80]})")

                # Prepare processed article for DB
                processed_article = {
                    'keyword': article.get('keyword', ''),
                    'title': article_for_json['title'],
                    'link': article_for_json['link'],
                    'google_link': article_for_json['google_link'],
                    'published': published,
                    'source': article.get('source', ''),
                    'body_path': body_path
                }
                processed.append(processed_article)

            except Exception as e:
                logger.error(f"Error processing article: {e}")
                continue

        logger.info(f"Processed {len(processed)} articles")
        return processed

    def merge_rss_and_scraped_data(
        self,
        rss_articles: List[Dict],
        scraped_articles: List[Dict]
    ) -> List[Dict]:
        """
        Merge RSS feed data with scraped article content

        Args:
            rss_articles: Articles from RSS feed
            scraped_articles: Scraped article content

        Returns:
            Merged article list
        """
        # Create a mapping of URL to scraped content
        scraped_map = {
            article.get('url'): article
            for article in scraped_articles
        }

        merged = []
        for rss_article in rss_articles:
            link = rss_article.get('link')
            merged_article = rss_article.copy()

            # Add scraped content if available
            if link in scraped_map:
                scraped_data = scraped_map[link]
                merged_article.update({
                    'body': scraped_data.get('content', ''),
                })

            merged.append(merged_article)

        logger.info(f"Merged {len(merged)} articles")
        return merged

    def get_statistics(self, data: List[Dict]) -> Dict:
        """
        Get statistics about the data

        Args:
            data: List of article dictionaries

        Returns:
            Statistics dictionary
        """
        stats = {
            'total_articles': len(data),
            'sources': {},
            'date_range': {
                'earliest': None,
                'latest': None
            }
        }

        # Count by source
        for article in data:
            source = article.get('source', 'Unknown')
            stats['sources'][source] = stats['sources'].get(source, 0) + 1

        # Date range (if available)
        dates = [
            article.get('published')
            for article in data
            if article.get('published')
        ]
        if dates:
            stats['date_range']['earliest'] = min(dates)
            stats['date_range']['latest'] = max(dates)

        return stats


