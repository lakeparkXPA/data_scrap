"""
Test URL resolution with latest RSS feed URLs
"""
import requests
from src.rss_fetcher import RSSFetcher
from src.data_processor import DataProcessor
from config.config import Config

# Initialize
config = Config()
rss_fetcher = RSSFetcher(config)
processor = DataProcessor(config)

# Fetch latest articles
print("Fetching latest articles from RSS...")
feed = rss_fetcher.fetch_by_keyword("AI")

if feed:
    articles = rss_fetcher.parse_entries(feed)
    print(f"Found {len(articles)} articles\n")

    # Test URL resolution
    for i, article in enumerate(articles[:2], 1):
        original_url = article.get('link', '')
        print(f"\n{'='*80}")
        print(f"Article {i}:")
        print(f"Title: {article.get('title', '')[:70]}...")
        print(f"\nOriginal URL: {original_url}")

        # Manual test with requests
        print("\nTesting with direct requests...")
        try:
            session = requests.Session()
            session.headers.update({'User-Agent': config.USER_AGENT})

            # Try HEAD request
            print("  Trying HEAD request...")
            resp = session.head(original_url, allow_redirects=True, timeout=10)
            print(f"    Status: {resp.status_code}")
            print(f"    Final URL: {resp.url}")
            print(f"    Redirects: {len(resp.history)}")

            # Try GET request
            print("  Trying GET request...")
            resp = session.get(original_url, allow_redirects=True, timeout=10)
            print(f"    Status: {resp.status_code}")
            print(f"    Final URL: {resp.url}")
            print(f"    Redirects: {len(resp.history)}")
            if resp.history:
                print(f"    Redirect chain:")
                for r in resp.history:
                    print(f"      {r.status_code}: {r.url[:80]}...")

        except Exception as e:
            print(f"  Error: {e}")

        # Test with processor method
        print("\n  Using processor.resolve_google_news_url()...")
        final_url = processor.resolve_google_news_url(original_url)
        print(f"    Result: {final_url}")

        # Check if resolution worked
        if original_url != final_url and 'news.google.com' not in final_url:
            print(f"\n  ✓ URL resolved successfully!")
        else:
            print(f"\n  ✗ URL unchanged or still on Google News")

else:
    print("Failed to fetch RSS feed")
