import time
import re

from backend.agents import (
    build_search_agent,
    writer_chain,
    critic_chain,
)

from backend.tools import scrape_webpage


def run_research_pipeline(topic: str) -> dict:

    state = {}

    # ============================================================
    # STEP 1 - SEARCH AGENT
    # ============================================================

    print("\n" + "=" * 50)
    print("STEP 1 - Search agent is working ...")
    print("=" * 50)

    search_agent = build_search_agent()

    # Small delay before the Mistral request
    time.sleep(10)

    search_result = search_agent.invoke({
        "messages": [
            (
                "user",
                f"Find recent, reliable and detailed information about: {topic}"
            )
        ]
    })

    state["search_results"] = search_result["messages"][-1].content

    print("\nSearch result:\n")
    print(state["search_results"])

    # ============================================================
    # STEP 2 - SCRAPE SOURCE DIRECTLY
    # ============================================================

    print("\n" + "=" * 50)
    print("STEP 2 - Scraping top resource directly ...")
    print("=" * 50)

    # Extract URLs from the search agent's response
    urls = re.findall(
        r'https?://[^\s\)\]]+',
        state["search_results"]
    )

    if urls:

        url = urls[0].rstrip(".,")
        print(f"\nScraping URL: {url}")

        try:
            state["scraped_content"] = scrape_webpage(url)

        except Exception as e:
            state["scraped_content"] = (
                f"Unable to scrape the source.\n"
                f"Error: {str(e)}"
            )

    else:

        state["scraped_content"] = (
            "No URL was found in the search results."
        )

    print("\nScraped content:\n")
    print(state["scraped_content"])

    # ============================================================
    # STEP 3 - WRITER
    # ============================================================

    print("\n" + "=" * 50)
    print("STEP 3 - Writer is drafting the report ...")
    print("=" * 50)

    research_combined = (
        f"SEARCH RESULTS:\n"
        f"{state['search_results']}\n\n"
        f"DETAILED SCRAPED CONTENT:\n"
        f"{state['scraped_content']}"
    )

    # Delay before Writer's Mistral request
    time.sleep(10)

    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research_combined,
    })

    print("\nFinal Report:\n")
    print(state["report"])

    # ============================================================
    # STEP 4 - CRITIC
    # ============================================================

    print("\n" + "=" * 50)
    print("STEP 4 - Critic is reviewing the report ...")
    print("=" * 50)

    # Temporarily skipped because Mistral rate limit
    # was being reached during the Critic request.

    state["feedback"] = (
        "Critic temporarily skipped because "
        "Mistral rate limit was reached."
    )

    print("\nCritic report:\n")
    print(state["feedback"])

    # ============================================================
    # RETURN FINAL STATE
    # ============================================================

    return state


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    topic = input("\nEnter a research topic: ")

    result = run_research_pipeline(topic)

    print("\n" + "=" * 50)
    print("RESEARCH PIPELINE COMPLETED")
    print("=" * 50)