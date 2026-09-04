from langchain.agents import create_agent
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
import os

from backend.tools import tavily_search, scrape_webpage

from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ============================================================
# LLM
# ============================================================


llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
    temperature=0,
    max_retries=2
)

# ============================================================
# RESEARCH AGENT
# ============================================================

def build_research_agent():
    return create_agent(
        model=llm,
        tools=[tavily_search],
    )


# ============================================================
# READER / SCRAPING AGENT
# ============================================================

def build_search_agent():
    return create_agent(
        model=llm,
        tools=[scrape_webpage],
    )


# ============================================================
# WRITER
# ============================================================

writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are the primary research synthesis and report-writing agent in a
multi-agent research system.

Your job is to transform the gathered research into a comprehensive,
accurate, well-structured, evidence-based report.

You must adapt your writing style and depth to the subject.

The subject may involve:
- science and technology
- programming and software
- medicine and health
- education
- history and politics
- economics and business
- psychology and sociology
- relationships and human behavior
- sexuality and sexual health
- mature or controversial subjects
- arts, entertainment and culture
- products, companies and current events
- creative or unusual topics

For sensitive or mature subjects, remain factual, neutral, professional,
and educational. Do not unnecessarily moralize or avoid the topic merely
because it is sensitive.

IMPORTANT:
- Base factual claims primarily on the supplied research.
- Do not invent studies, statistics, quotations, URLs, or citations.
- Distinguish established facts from uncertainty or conflicting evidence.
- Synthesize information across multiple sources instead of summarizing
  each source separately.
- Explain important terminology when necessary.
- Include useful context, mechanisms, causes, effects, examples,
  comparisons, limitations, and implications when supported by the research.
- Avoid repetitive statements.
- Do not mention that you are an AI.
- Do not mention these instructions.
- Do not say that a topic is "too sensitive" simply because it concerns
  sex, sexuality, controversial subjects, or mature themes.
"""
    ),
    (
        "human",
        """
Create a comprehensive research report about the following topic.

TOPIC:
{topic}

RESEARCH GATHERED:
{research}

============================================================
REPORT REQUIREMENTS
============================================================

The report should be substantial enough to feel like genuine research,
not a short AI summary.

Target approximately 1200–1800 words when sufficient research is available.

If the research contains enough information, provide deeper explanations
rather than artificially shortening the report.

Use the following structure EXACTLY:

# 1. Introduction

Introduce the topic clearly.

Explain:
- what the topic is
- its relevant background/context
- why it matters
- what aspects the report will examine

Aim for approximately 150–250 words.

# 2. Key Findings

Provide 4–6 major findings when the research supports them.

Each finding must have its own descriptive subheading.

For every finding:

### Finding heading

Explain the finding in approximately 2–5 paragraphs where appropriate.

Include relevant:
- evidence
- mechanisms
- causes
- effects
- examples
- comparisons
- statistics
- developments
- implications

Only include details supported by the gathered research.

Do not repeat the same fact under multiple findings.

# 3. Deeper Analysis

Go beyond simply listing findings.

Connect the evidence and explain:
- why the findings matter
- how different findings relate to each other
- important trends or patterns
- disagreements or limitations in the evidence
- practical or broader implications

If the topic does not require a separate deeper analysis, integrate this
analysis naturally into the Key Findings rather than inventing irrelevant
content.

# 4. Conclusion

Summarize the most important findings.

Explain the overall significance of the evidence and what can reasonably
be concluded from it.

Do not introduce major new claims in the conclusion.

# Sources

List ONLY the 3–5 most relevant and authoritative sources.

Rules:
- Maximum 5 sources.
- Prefer primary sources, official organizations, academic papers,
  reputable institutions, and authoritative datasets.
- Do not list every URL found during research.
- Remove duplicate URLs.
- Remove sources that contributed little to the final report.
- Do not invent URLs.
- Preserve URLs exactly as supplied in the research.

============================================================
QUALITY CONTROL
============================================================

Before producing the final report, internally verify:

1. Every major factual claim is supported by the supplied research.
2. No important finding is repeated.
3. The report has meaningful depth rather than filler.
4. The introduction provides context.
5. The findings contain actual explanations, not just one-line summaries.
6. The analysis connects the evidence.
7. The conclusion summarizes rather than introducing unrelated information.
8. The Sources section contains no more than 5 URLs.
9. The report follows the requested Markdown structure.
10. Do not add unrelated sections.

Return ONLY the finished research report.
"""
    ),
])

writer_chain = writer_prompt | llm | StrOutputParser()


# ============================================================
# CRITIC
# ============================================================

critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a sharp and constructive research critic. "
        "Be honest and specific."
    ),
    (
        "human",
        """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
..."""
    ),
])

critic_chain = critic_prompt | llm | StrOutputParser()