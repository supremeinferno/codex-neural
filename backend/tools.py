from langchain.tools import tool
from tavily import TavilyClient
from bs4 import BeautifulSoup
import requests
import os

from rich import print
from rich.console import Console
from rich.table import Table


from dotenv import load_dotenv
load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Roughly 4 characters ~= 1 token. Keeping scraped pages under ~16,000
# characters (~4,000 tokens) leaves headroom under Groq's free-tier
# 8,000 TPM limit once the system prompt, tool schema, and conversation
# history are counted too.
MAX_SCRAPE_CHARS = 16000


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

        if len(text) > MAX_SCRAPE_CHARS:
            text = (
                text[:MAX_SCRAPE_CHARS]
                + "\n\n[Content truncated to stay within model token limits.]"
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