from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from backend.agents import llm


technical_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
Provide your interpretation of the user's research request while keeping the following in mind. Rewrite it to eliminate any ambiguities. Do not ask the user for clarification or answer the request. Provide your interpretation of the request and append any assumptions you make. Also append your assumption of user's background knowledge and assumption of the depth of question and the expected answer. Replace words like it, they, that, this, etc. with the specific subject they refer to. Use ASD-STE100 guidelines (like- one word=one meaning, use active voice, one instruction per sentence, keep sentences short, avoid noun clusters, use articles, and avoid pronouns etc.).

Return the rewritten prompt with appended imformatation. It can present assumptions very concisely, even as simply as key-value pairs so that the gist is apparent for the user to review and make any necessary adjustments. The Returned prompt is to be used as a prompt for a technical expert to answer the research request. It should be concise, non-repetitive, the first sentence should be the gist of the request in plain text, and the rest of the prompt should be the assumptions and clarifications. The rewritten prompt should be in a format that is easy to read and understand and without any markers like **. If some background knowlegde is neccesarily assumed, it should be stated too.


"""
    ),
    (
        "human",
        "Rewrite this research query:\n\n{topic}"
    ),
])

technical_chain = technical_prompt | llm | StrOutputParser()


def rewrite_research_prompt(topic: str) -> str:
    rewritten_prompt = technical_chain.invoke({"topic": topic}).strip()
    if not rewritten_prompt:
        raise ValueError("The technical prompt rewrite was empty.")
    return rewritten_prompt
