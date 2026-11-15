from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from backend.agents import llm


technical_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You rewrite a user's research request into one clear, technically precise
prompt for a web research system.

Preserve the user's intent. Make the requested subject, scope, context,
assumptions, and expected depth explicit when they can reasonably be inferred.
State important assumptions in the rewritten prompt instead of presenting
them as facts. Do not answer the request, add unsupported factual claims, or
ask follow-up questions. Return only the rewritten prompt as plain text.
"""
    ),
    (
        "human",
        "Rewrite this research request:\n\n{topic}"
    ),
])

technical_chain = technical_prompt | llm | StrOutputParser()


def rewrite_research_prompt(topic: str) -> str:
    rewritten_prompt = technical_chain.invoke({"topic": topic}).strip()
    if not rewritten_prompt:
        raise ValueError("The technical prompt rewrite was empty.")
    return rewritten_prompt
