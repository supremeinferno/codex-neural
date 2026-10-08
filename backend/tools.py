from langchain.tools import tool
from tavily import TavilyClient
from bs4 import BeautifulSoup
import requests

from backend.config import settings


tavily = TavilyClient(api_key=settings.tavily_api_key)


@tool
def tavily_search(query: str) -> list:
    """Search the web using Tavily and return title, URL, and a 100-word snippet."""

    response = tavily.search(
        query=query,
        max_results=5
    )

    results = []

    for result in response["results"]:
        content = result.get("content", "")

        snippet = " ".join(content.split()[:100])

        results.append({
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "snippet": snippet
        })

    return results


@tool
def scrape_webpage(url: str) -> str:
    """Scrape and return the full readable text content from a webpage URL."""

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Remove elements that don't contain useful article text
        for element in soup([
            "script",
            "style",
            "nav",
            "header",
            "footer",
            "aside",
            "form"
        ]):
            element.decompose()

        text = soup.get_text(
            separator=" ",
            strip=True
        )

        return text

    except requests.exceptions.HTTPError as e:
        return f"Unable to scrape webpage because of HTTP error: {e}"

    except requests.exceptions.Timeout:
        return "Unable to scrape webpage because the request timed out."

    except requests.exceptions.ConnectionError:
        return "Unable to scrape webpage because the connection failed."

    except requests.exceptions.RequestException as e:
        return f"Unable to scrape webpage: {e}"

    except Exception as e:
        return f"Unexpected scraping error: {e}"