"""
Web Scraper for article content extraction
"""
import requests
from bs4 import BeautifulSoup
import logging
import time
import json
from typing import Optional, Dict
from config.config import Config


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebScraper:
    """웹 스크래핑 클래스"""

    def __init__(self, config: Config = None):
        """
        Initialize Web Scraper

        Args:
            config: Configuration object
        """
        self.config = config or Config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch HTML content from URL

        Args:
            url: Target URL

        Returns:
            HTML content string or None if failed
        """
        for attempt in range(self.config.MAX_RETRIES):
            try:
                logger.info(f"Fetching page: {url} (attempt {attempt + 1})")
                response = self.session.get(
                    url,
                    timeout=self.config.REQUEST_TIMEOUT
                )
                response.raise_for_status()
                return response.text

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    time.sleep(self.config.RETRY_DELAY)
                else:
                    logger.error(f"Failed to fetch page after {self.config.MAX_RETRIES} attempts")
                    return None

    def parse_article(self, html: str, url: str) -> Dict:
        """
        Parse article content from HTML (with LLM fallback)

        Args:
            html: HTML content
            url: Source URL

        Returns:
            Dictionary containing extracted article data
        """
        try:
            soup = BeautifulSoup(html, 'lxml')

            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Try BeautifulSoup extraction first
            content = self._extract_content(soup)

            # If BeautifulSoup fails, try LLM
            if not content or len(content) < 100:
                logger.info(f"BeautifulSoup extraction insufficient, trying LLM for {url[:80]}...")
                content = self._extract_content_with_llm(html, url)

            article_data = {
                'url': url,
                'content': content,
                'meta_description': self._extract_meta_description(soup),
                'author': self._extract_author(soup),
                'publish_date': self._extract_publish_date(soup),
            }

            return article_data

        except Exception as e:
            logger.error(f"Error parsing article: {e}")
            return {'url': url, 'error': str(e)}

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title"""
        # Try multiple selectors
        selectors = [
            ('meta', {'property': 'og:title'}),
            ('meta', {'name': 'twitter:title'}),
            'h1',
            'title'
        ]

        for selector in selectors:
            if isinstance(selector, tuple):
                tag = soup.find(selector[0], selector[1])
                if tag and tag.get('content'):
                    return tag.get('content').strip()
            else:
                tag = soup.find(selector)
                if tag:
                    return tag.get_text().strip()

        return ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content"""
        # Try common article containers with class matching
        # Main tag is first priority as it works for electrek.co
        selectors = [
            ('main', {}),
            ('main', {'role': 'main'}),
            ('article', {}),
            ('div', {'class': lambda x: x and 'article-content' in str(x)}),
            ('div', {'class': lambda x: x and 'post-content' in str(x)}),
            ('div', {'class': lambda x: x and 'entry-content' in str(x)}),
            ('div', {'class': lambda x: x and 'article-body' in str(x)}),
            ('div', {'class': lambda x: x and 'story-body' in str(x)}),
            ('div', {'class': lambda x: x and 'ArticleBody' in str(x)}),
            ('div', {'class': lambda x: x and 'story-content' in str(x)}),
            ('div', {'id': 'article-body'}),
        ]

        for selector in selectors:
            tag = soup.find(selector[0], selector[1])
            if tag:
                # Get all paragraphs
                paragraphs = tag.find_all('p')
                if paragraphs:
                    # Filter out very short paragraphs (likely captions, labels, etc.)
                    filtered_paragraphs = [p.get_text().strip() for p in paragraphs if p.get_text().strip() and len(p.get_text().strip()) > 30]
                    if filtered_paragraphs:
                        content = '\n\n'.join(filtered_paragraphs)
                        if len(content) > 100:  # Minimum content length
                            logger.info(f"Content extracted using selector: {selector[0]} with {len(filtered_paragraphs)} paragraphs")
                            return content

        # Fallback: get all paragraphs from body
        paragraphs = soup.find_all('p')
        if paragraphs:
            filtered_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50]
            if filtered_paragraphs:
                content = '\n\n'.join(filtered_paragraphs)
                if len(content) > 100:
                    logger.info(f"Content extracted using fallback method with {len(filtered_paragraphs)} paragraphs")
                    return content

        logger.warning("No content could be extracted using BeautifulSoup")
        return ""

    def _extract_content_with_llm(self, html: str, url: str) -> str:
        """
        Extract article content using LLM as fallback

        Args:
            html: Raw HTML content
            url: Article URL

        Returns:
            Extracted article content
        """
        if not self.config.LLM_ENABLED:
            logger.info("LLM extraction disabled")
            return ""

        try:
            # Clean HTML - remove scripts, styles, etc
            soup = BeautifulSoup(html, 'lxml')
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
                element.decompose()

            # Get text content (simplified)
            text_content = soup.get_text(separator='\n', strip=True)

            # Limit content length to avoid token limits
            if len(text_content) > 10000:
                text_content = text_content[:10000]

            # Prepare prompt for LLM
            prompt = f"""Extract the main article content from the following text. Return ONLY the article body text, without any navigation, ads, or other non-article content. Do not include any explanations or metadata.

Text from {url}:
{text_content}

Article content:"""

            # Call Ollama API
            response = requests.post(
                f"{self.config.LLM_API_BASE}/api/generate",
                json={
                    "model": self.config.LLM_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=self.config.LLM_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get('response', '').strip()
                if len(content) > 100:
                    logger.info(f"Content extracted using LLM ({len(content)} chars)")
                    return content
                else:
                    logger.warning("LLM returned too short content")
                    return ""
            else:
                logger.error(f"LLM API error: {response.status_code}")
                return ""

        except Exception as e:
            logger.error(f"Error extracting content with LLM: {e}")
            return ""

    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description"""
        meta_tags = [
            ('meta', {'property': 'og:description'}),
            ('meta', {'name': 'description'}),
            ('meta', {'name': 'twitter:description'}),
        ]

        for tag_name, attrs in meta_tags:
            tag = soup.find(tag_name, attrs)
            if tag and tag.get('content'):
                return tag.get('content').strip()

        return ""

    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract article author"""
        selectors = [
            ('meta', {'name': 'author'}),
            ('meta', {'property': 'article:author'}),
            ('span', {'class': 'author'}),
            ('div', {'class': 'author'}),
            ('a', {'rel': 'author'}),
        ]

        for selector in selectors:
            if isinstance(selector, tuple):
                tag = soup.find(selector[0], selector[1])
                if tag:
                    content = tag.get('content') if tag.get('content') else tag.get_text()
                    if content:
                        return content.strip()

        return ""

    def _extract_publish_date(self, soup: BeautifulSoup) -> str:
        """Extract publish date"""
        selectors = [
            ('meta', {'property': 'article:published_time'}),
            ('meta', {'name': 'publish_date'}),
            ('time', {}),
        ]

        for selector in selectors:
            tag = soup.find(selector[0], selector[1])
            if tag:
                # Try datetime attribute first
                date = tag.get('datetime') or tag.get('content') or tag.get_text()
                if date:
                    return date.strip()

        return ""

    def scrape_article(self, url: str) -> Dict:
        """
        Scrape full article from URL

        Args:
            url: Article URL

        Returns:
            Dictionary containing article data
        """
        html = self.fetch_page(url)
        if html:
            return self.parse_article(html, url)
        else:
            # Return empty content instead of error to continue processing
            logger.warning(f"Could not fetch article, returning empty content: {url}")
            return {'url': url, 'content': '', 'error': 'Failed to fetch page'}

    def scrape_multiple_articles(self, urls: list) -> list:
        """
        Scrape multiple articles

        Args:
            urls: List of article URLs

        Returns:
            List of article data dictionaries
        """
        results = []
        for i, url in enumerate(urls):
            logger.info(f"Scraping article {i + 1}/{len(urls)}")
            article_data = self.scrape_article(url)
            results.append(article_data)

            # Be polite, add delay between requests
            if i < len(urls) - 1:
                time.sleep(1)

        return results


# Example usage
if __name__ == "__main__":
    from googlenewsdecoder import new_decoderv1

    scraper = WebScraper()

    # Test with Google News redirect URL
    google_news_url = "https://news.google.com/rss/articles/CBMiigFBVV95cUxPY1ZRYjh4YS1iSWNiV1Jzc29MU3RMMEZhSVdhOThqUzNxZlRsRm1MaW4xQy1ocnZScFh5ejR0MDBYbDRPLWx3X3lMM2wzMGU5VUxiWk9wR0ZINTVEVVNIQkpyZjFyMG5zRU1Pcl9xVEJPVmFXblI2OXVCdmZZSG1nRUhkc3dYbjNCWmc?oc=5"

    # Decode Google News URL to get actual article URL
    result = new_decoderv1(google_news_url, interval=1)

    # Extract URL from dictionary
    if isinstance(result, dict):
        actual_url = result.get('decoded_url', '')
    else:
        actual_url = result

    print(f"Google News URL: {google_news_url[:60]}...")
    print(f"Actual URL: {actual_url}")

    # Scrape article from actual URL
    article = scraper.scrape_article(actual_url)
    print(f"\nTitle: {article.get('title')}")
    print(f"Content length: {len(article.get('content', ''))}")
    print(article.get('content', ''))

    # Note: In production, use DataProcessor.resolve_google_news_url() instead
