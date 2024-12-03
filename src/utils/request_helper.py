import os


def build_url_with_scraper_api(url):
    """
    Builds a URL with the ScraperAPI endpoint and required query parameters.

    This function constructs a URL to access the ScraperAPI service by appending the provided URL
    as a query parameter along with an API key fetched from the environment variable `SCRAPER_API_KEY`.
    The resulting URL is used to send requests to the ScraperAPI service for web scraping purposes.

    Args:
        url (str): The URL of the webpage to be scraped.

    Returns:
        str: A string containing the full ScraperAPI URL with the provided URL and the API key as query parameters.
    """
    return f'http://api.scraperapi.com?api_key={os.getenv("SCRAPER_API_KEY")}&url={url}'
