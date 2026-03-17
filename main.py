"""
Main execution script for Google News RSS scraper
"""
import argparse
from config.config import Config
from src.rss_fetcher import RSSFetcher
from src.scraper import WebScraper
from src.data_processor import DataProcessor
from src.utils import setup_logger, format_article_summary


def main():
    """Main execution function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Google News RSS Scraper')
    parser.add_argument(
        '--keywords',
        nargs='+',
        help='Keywords to search (space-separated)',
        default=None
    )
    parser.add_argument(
        '--max-articles',
        type=int,
        help='Maximum number of articles to fetch per keyword (default: all)',
        default=None
    )
    parser.add_argument(
        '--d-after',
        type=str,
        default=None,
        help='Start date for search (YYYY-MM-DD format, e.g., 2026-03-01)'
    )
    parser.add_argument(
        '--d-before',
        type=str,
        default=None,
        help='End date for search (YYYY-MM-DD format, e.g., 2026-03-08)'
    )

    args = parser.parse_args()

    # Setup logger
    logger = setup_logger(
        'main',
        log_file=str(Config.LOG_DIR / 'scraper.log')
    )

    logger.info("=" * 50)
    logger.info("Starting Google News RSS Scraper")
    logger.info("=" * 50)

    # Initialize components
    config = Config()
    rss_fetcher = RSSFetcher(config)
    scraper = WebScraper(config)
    processor = DataProcessor(config)

    # Determine keywords
    keywords = args.keywords or config.DEFAULT_KEYWORDS
    logger.info(f"Keywords: {keywords}")

    # Log date range if provided
    if args.d_after or args.d_before:
        logger.info(f"Date range: after={args.d_after}, before={args.d_before}")

    # Fetch RSS feeds
    all_articles = []

    # Fetch by keywords
    results = rss_fetcher.fetch_multiple_keywords(
        keywords,
        d_after=args.d_after,
        d_before=args.d_before
    )

    for keyword, articles in results.items():
        logger.info(f"Found {len(articles)} articles for '{keyword}'")
        if args.max_articles:
            all_articles.extend(articles[:args.max_articles])
        else:
            all_articles.extend(articles)

    logger.info(f"Total articles fetched: {len(all_articles)}")

    if not all_articles:
        logger.warning("No articles found. Exiting.")
        return

    # Remove duplicates
    all_articles = processor.remove_duplicates(all_articles, key='link')
    logger.info(f"Articles after deduplication: {len(all_articles)}")

    # Resolve Google News redirect URLs
    logger.info("Resolving Google News redirect URLs...")
    all_articles = processor.resolve_urls(all_articles)

    # Always scrape full content for keyword-based search
    logger.info("Scraping full article content...")
    urls = [article['link'] for article in all_articles]
    scraped_articles = scraper.scrape_multiple_articles(urls)

    # Merge RSS and scraped data
    all_articles = processor.merge_rss_and_scraped_data(
        all_articles,
        scraped_articles
    )

    # Process articles (this will save JSON files and return articles with body_path)
    processed_articles = processor.process_articles(all_articles, save_json=True)

    # Save data - JSON files are already saved in process_articles
    output_info = []
    output_info.append(f"JSON: Saved {len(processed_articles)} individual article files to data/news/")

    # Always save to database
    try:
        db_count = processor.save_to_db(processed_articles)
        output_info.append(f"Database: {db_count} records saved")
    except Exception as e:
        logger.error(f"Failed to save to database: {e}")
        output_info.append(f"Database: Failed ({e})")

    # Display statistics
    stats = processor.get_statistics(processed_articles)
    logger.info("\n" + "=" * 50)
    logger.info("Statistics:")
    logger.info(f"Total articles: {stats['total_articles']}")
    logger.info(f"Sources: {len(stats['sources'])}")
    for source, count in stats['sources'].items():
        logger.info(f"  - {source}: {count}")

    if stats['date_range']['earliest']:
        logger.info(f"Date range: {stats['date_range']['earliest']} to {stats['date_range']['latest']}")

    logger.info("=" * 50)
    for info in output_info:
        logger.info(f"Data saved - {info}")
    logger.info("Scraping completed successfully!")

    # Close database connection
    processor.close_connection()

    # Print sample articles
    print("\n" + "=" * 70)
    print("SAMPLE ARTICLES")
    print("=" * 70)
    for i, article in enumerate(processed_articles[:3], 1):
        print(f"\n[Article {i}]")
        print(format_article_summary(article))
        print("-" * 70)


if __name__ == "__main__":
    main()
