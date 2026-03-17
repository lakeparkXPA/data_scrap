"""
Utility functions
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logger(name: str, log_file: Optional[str] = None, level=logging.INFO) -> logging.Logger:
    """
    Set up logger with file and console handlers

    Args:
        name: Logger name
        log_file: Path to log file (optional)
        level: Logging level

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log_file specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_timestamp(format_str: str = "%Y%m%d_%H%M%S") -> str:
    """
    Get current timestamp as formatted string

    Args:
        format_str: Datetime format string

    Returns:
        Formatted timestamp string
    """
    return datetime.now().strftime(format_str)


def ensure_directory(path: Path) -> None:
    """
    Ensure directory exists, create if necessary

    Args:
        path: Directory path
    """
    path.mkdir(parents=True, exist_ok=True)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length

    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to append if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    return filename


def parse_google_news_url(url: str) -> Optional[str]:
    """
    Extract actual article URL from Google News redirect URL

    Args:
        url: Google News URL

    Returns:
        Actual article URL or None
    """
    try:
        # Google News URLs often contain the actual URL in query parameters
        if 'news.google.com' in url:
            # This is a simplified version - actual implementation may need
            # to handle different URL patterns
            import urllib.parse
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)

            # Try to find the actual URL in common parameters
            for param in ['url', 'link', 'article']:
                if param in params:
                    return params[param][0]

        return url

    except Exception:
        return url


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """
    Estimate reading time in minutes

    Args:
        text: Article text
        words_per_minute: Average reading speed

    Returns:
        Estimated reading time in minutes
    """
    if not text:
        return 0

    word_count = len(text.split())
    reading_time = max(1, round(word_count / words_per_minute))

    return reading_time


def format_article_summary(article: dict, max_length: int = 200) -> str:
    """
    Format article as a summary string

    Args:
        article: Article dictionary
        max_length: Maximum summary length

    Returns:
        Formatted summary string
    """
    title = article.get('title', 'No title')
    source = article.get('source', 'Unknown source')
    published = article.get('published', 'Unknown date')
    summary = article.get('body', '')

    summary_text = truncate_text(summary, max_length)

    return f"""
Title: {title}
Source: {source}
Published: {published}
Summary: {summary_text}
    """.strip()


# Example usage
if __name__ == "__main__":
    # Test logger setup
    logger = setup_logger('test_logger', 'logs/test.log')
    logger.info("Test log message")

    # Test timestamp
    print(f"Timestamp: {get_timestamp()}")

    # Test text truncation
    long_text = "This is a very long text that needs to be truncated" * 10
    print(f"Truncated: {truncate_text(long_text, 50)}")

    # Test filename sanitization
    unsafe_filename = "file:name?with*invalid<chars>"
    print(f"Safe filename: {sanitize_filename(unsafe_filename)}")
