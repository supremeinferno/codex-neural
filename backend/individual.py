import os
import re
import hashlib
import fitz

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain_text_splitters import RecursiveCharacterTextSplitter


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INDIVIDUAL_DB_PATH = os.path.join(
    BASE_DIR,
    "individual_chroma"
)

COLLECTION_NAME = "individual_documents"


def load_embeddings():
    return MistralAIEmbeddings()


def make_document_id(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()[:12]


def looks_like_heading(text):
    text = text.strip()

    if not text or len(text) > 150:
        return False

    patterns = [
        r"^\d+\.\s+.+",
        r"^\d+\.\d+\s+.+",
        r"^\d+\.\d+\.\d+\s+.+",
        r"^(abstract|introduction|background|"
        r"related work|methodology|methods|"
        r"experiments|evaluation|results|discussion|"
        r"conclusion|limitations|references)$"
    ]

    return any(
        re.match(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


def clean_heading(text):
    return " ".join(text.split())


def extract_pdf_documents(pdf_path, document_id, document_name):
    pdf = fitz.open(pdf_path)

    documents = []
    current_section = "Unknown"

    for page_index, page in enumerate(pdf):
        page_number = page_index + 1

        text = page.get_text("text")

        if not text.strip():
            continue

        page_lines = []

        for line in text.splitlines():
            line = line.strip()

            if not line:
                continue

            if looks_like_heading(line):
                current_section = clean_heading(line)
            else:
                page_lines.append(line)

        page_text = "\n".join(page_lines)

        if not page_text.strip():
            continue

        documents.append(
            Document(
                page_content=page_text,
                metadata={
                    "document_id": document_id,
                    "document_name": document_name,
                    "page": page_number,
                    "section": current_section,
                    "content_type": "text"
                }
            )
        )

    pdf.close()

    return documents


def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=200,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ]
    )

    chunks = splitter.split_documents(documents)

    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"chunk_{index}"

    return chunks


def build_individual_index(pdf_bytes, document_name):
    os.makedirs(
        INDIVIDUAL_DB_PATH,
        exist_ok=True
    )

    document_id = make_document_id(pdf_bytes)

    pdf_path = os.path.join(
        INDIVIDUAL_DB_PATH,
        f"{document_id}.pdf"
    )

    if not os.path.exists(pdf_path):
        with open(pdf_path, "wb") as file:
            file.write(pdf_bytes)

    documents = extract_pdf_documents(
        pdf_path,
        document_id,
        document_name
    )

    if not documents:
        return {
            "success": False,
            "message": "No readable text was found in the PDF.",
            "document_id": document_id,
            "pages": 0,
            "chunks": 0
        }

    chunks = chunk_documents(documents)

    if not chunks:
        return {
            "success": False,
            "message": "Unable to create searchable chunks.",
            "document_id": document_id,
            "pages": len(documents),
            "chunks": 0
        }

    vectorstore = Chroma(
        persist_directory=INDIVIDUAL_DB_PATH,
        collection_name=COLLECTION_NAME,
        embedding_function=load_embeddings()
    )

    existing = vectorstore.get(
        where={
            "document_id": document_id
        },
        include=[]
    )

    existing_ids = existing.get("ids", [])

    if existing_ids:
        return {
            "success": True,
            "message": "PDF is already indexed.",
            "document_id": document_id,
            "document_name": document_name,
            "pages": len(documents),
            "chunks": len(existing_ids)
        }

    vectorstore.add_documents(chunks)

    return {
        "success": True,
        "message": "PDF indexed successfully.",
        "document_id": document_id,
        "document_name": document_name,
        "pages": len(documents),
        "chunks": len(chunks)
    }


def is_summary_question(question):
    question_lower = question.lower().strip()

    summary_phrases = [
        "summarize",
        "summarise",
        "summary",
        "summarize this",
        "summarise this",
        "overview",
        "overall",
        "give me an overview",
        "give me a summary",
        "summarize the document",
        "summarise the document",
        "summary of the document",
        "summary of this document",
        "what is this paper about",
        "what is this document about",
        "explain the whole document",
        "explain the entire document"
    ]

    return any(
        phrase in question_lower
        for phrase in summary_phrases
    )


def generate_full_document_summary(
    vectorstore,
    document_id
):
    result = vectorstore.get(
        where={
            "document_id": document_id
        },
        include=[
            "documents",
            "metadatas"
        ]
    )

    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])

    if not documents:
        return None

    combined = []

    for content, metadata in zip(documents, metadatas):
        combined.append(
            {
                "page": metadata.get("page", 0),
                "chunk_id": metadata.get("chunk_id", ""),
                "section": metadata.get(
                    "section",
                    "Unknown"
                ),
                "content": content
            }
        )

    combined.sort(
        key=lambda item: (
            item["page"],
            item["chunk_id"]
        )
    )

    context_parts = []

    for item in combined:
        context_parts.append(
            f"Page {item['page']} "
            f"({item['section']}):\n"
            f"{item['content']}"
        )

    full_context = "\n\n".join(context_parts)

    # Prevent extremely large documents from exceeding
    # the model context window.
    max_characters = 90000

    if len(full_context) > max_characters:
        full_context = full_context[:max_characters]

    llm = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0,
        timeout=120,
        max_retries=0
    )

    prompt = f"""
You are an expert document analysis assistant.

Create a comprehensive summary of the uploaded PDF.

Use the provided document content as your ONLY source.

The summary should cover:

1. Main topic and purpose
2. Important concepts
3. Methodology or approach
4. Key findings or results
5. Important arguments or observations
6. Limitations, if mentioned
7. Conclusion
8. Important details that a reader should remember

Organize the answer with clear headings and concise bullet points.

Do not invent information that is not present in the document.

DOCUMENT CONTENT:

{full_context}
"""

    response = llm.invoke(prompt)

    return response.content


def answer_individual_question(question, document_id):
    vectorstore = Chroma(
        persist_directory=INDIVIDUAL_DB_PATH,
        collection_name=COLLECTION_NAME,
        embedding_function=load_embeddings()
    )

    # Full-document summary mode
    if is_summary_question(question):
        answer = generate_full_document_summary(
            vectorstore,
            document_id
        )

        if not answer:
            return {
                "success": False,
                "message": "No indexed content was found for this PDF."
            }

        return {
            "success": True,
            "answer": answer,
            "sources": []
        }

    # Normal question mode
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,
            "fetch_k": 10,
            "lambda_mult": 0.5,
            "filter": {
                "document_id": document_id
            }
        }
    )

    relevant_documents = retriever.invoke(question)

    if not relevant_documents:
        return {
            "success": False,
            "message": "I could not find relevant information in this PDF."
        }

    context = "\n\n".join(
        [
            f"Page {doc.metadata.get('page', 'Unknown')}:\n"
            f"{doc.page_content}"
            for doc in relevant_documents
        ]
    )

    llm = ChatMistralAI(
        model="mistral-small-latest",
        temperature=0,
        timeout=120,
        max_retries=0
    )

    prompt = f"""
You are a PDF document assistant.

Answer the user's question using ONLY the
information provided in the PDF context below.

If the answer cannot be found in the context,
clearly say that the information is not available
in the uploaded PDF.

Mention page numbers when useful.

PDF CONTEXT:

{context}

USER QUESTION:

{question}
"""

    response = llm.invoke(prompt)

    return {
        "success": True,
        "answer": response.content,
        "sources": [
            {
                "page": doc.metadata.get("page"),
                "section": doc.metadata.get(
                    "section",
                    "Unknown"
                )
            }
            for doc in relevant_documents
        ]
    }