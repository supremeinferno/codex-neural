import os
import re
import time
import hashlib
import fitz

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_mistralai import MistralAIEmbeddings
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "..", ".env"))
INDIVIDUAL_DB_PATH = os.path.join(BASE_DIR, "individual_chroma")
COLLECTION_NAME = "individual_documents"
DOCUMENT_ID_PATTERN = re.compile(r"[a-f0-9]{12}")
GROQ_MODEL = "openai/gpt-oss-120b"
MAX_SUMMARY_CHARACTERS = 30000


def load_embeddings():
    return MistralAIEmbeddings()


def load_llm():
    return ChatGroq(model=GROQ_MODEL, api_key=os.getenv("GROQ_API_KEY"), temperature=0, timeout=120, max_retries=0)


def is_rate_limit_error(error):
    status = getattr(error, "status_code", None)
    if status is None:
        status = getattr(getattr(error, "response", None), "status_code", None)
    return status == 429 or ("429" in str(error) and "rate" in str(error).lower())


def invoke_with_retry(llm, prompt, attempts=3, wait_seconds=8):
    for attempt in range(attempts):
        try:
            return llm.invoke(prompt)
        except Exception as error:
            if not is_rate_limit_error(error) or attempt == attempts - 1:
                raise
            time.sleep(wait_seconds * (attempt + 1))


def make_document_id(file_bytes):
    return hashlib.md5(file_bytes).hexdigest()[:12]


def get_pdf_path(document_id):
    if not DOCUMENT_ID_PATTERN.fullmatch(document_id or ""):
        return None
    path = os.path.join(INDIVIDUAL_DB_PATH, f"{document_id}.pdf")
    return path if os.path.isfile(path) else None


def looks_like_heading(text):
    text = text.strip()
    if not text or len(text) > 150:
        return False
    patterns = [r"^\d+(?:\.\d+)*\.?\s+.+", r"^(abstract|introduction|background|related work|methodology|methods|experiments|evaluation|results|discussion|conclusion|limitations|references)$"]
    return any(re.match(pattern, text, re.IGNORECASE) for pattern in patterns)


def clean_heading(text):
    return " ".join(text.split())


def extract_pdf_documents(pdf_path, document_id, document_name):
    pdf = fitz.open(pdf_path)
    documents = []
    section = "Unknown"
    for page_index, page in enumerate(pdf):
        lines = []
        for raw_line in page.get_text("text").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if looks_like_heading(line):
                section = clean_heading(line)
            else:
                lines.append(line)
        text = "\n".join(lines)
        if text.strip():
            documents.append(Document(page_content=text, metadata={"document_id": document_id, "document_name": document_name, "page": page_index + 1, "section": section, "content_type": "text"}))
    pdf.close()
    return documents


def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(chunk_size=3000, chunk_overlap=200, separators=["\n\n", "\n", ". ", " ", ""])
    chunks = splitter.split_documents(documents)
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = f"chunk_{index:06d}"
    return chunks


def build_individual_index(pdf_bytes, document_name):
    os.makedirs(INDIVIDUAL_DB_PATH, exist_ok=True)
    document_id = make_document_id(pdf_bytes)
    pdf_path = os.path.join(INDIVIDUAL_DB_PATH, f"{document_id}.pdf")
    if not os.path.exists(pdf_path):
        with open(pdf_path, "wb") as file:
            file.write(pdf_bytes)
    try:
        documents = extract_pdf_documents(pdf_path, document_id, document_name)
    except Exception as error:
        return {"success": False, "message": f"Unable to read PDF: {error}", "document_id": document_id, "document_name": document_name, "pages": 0, "chunks": 0}
    if not documents:
        return {"success": False, "message": "No readable text was found in the PDF.", "document_id": document_id, "document_name": document_name, "pages": 0, "chunks": 0}
    chunks = chunk_documents(documents)
    if not chunks:
        return {"success": False, "message": "Unable to create searchable chunks.", "document_id": document_id, "document_name": document_name, "pages": len(documents), "chunks": 0}
    vectorstore = Chroma(persist_directory=INDIVIDUAL_DB_PATH, collection_name=COLLECTION_NAME, embedding_function=load_embeddings())
    existing = vectorstore.get(where={"document_id": document_id}, include=[])
    existing_ids = existing.get("ids", [])
    if existing_ids:
        return {"success": True, "message": "PDF is already indexed.", "document_id": document_id, "document_name": document_name, "pages": len(documents), "chunks": len(existing_ids)}
    vectorstore.add_documents(chunks)
    return {"success": True, "message": "PDF indexed successfully.", "document_id": document_id, "document_name": document_name, "pages": len(documents), "chunks": len(chunks)}


def _validate_document_ids(document_ids):
    if not isinstance(document_ids, list) or not document_ids:
        return None, "Select at least one document."
    valid = []
    for document_id in document_ids:
        if not isinstance(document_id, str) or not DOCUMENT_ID_PATTERN.fullmatch(document_id):
            return None, "Invalid document ID."
        if not get_pdf_path(document_id):
            return None, "One or more selected documents were not found."
        if document_id not in valid:
            valid.append(document_id)
    return valid, None


def _open_vectorstore():
    return Chroma(persist_directory=INDIVIDUAL_DB_PATH, collection_name=COLLECTION_NAME, embedding_function=load_embeddings())


def _retrieve(vectorstore, document_id, query, k=5, fetch_k=10, sections=None):
    where = {"document_id": document_id}
    retriever = vectorstore.as_retriever(search_type="mmr", search_kwargs={"k": k, "fetch_k": fetch_k, "lambda_mult": 0.5, "filter": where})
    docs = retriever.invoke(query)
    if sections:
        matching = [d for d in docs if any(word in str(d.metadata.get("section", "")).lower() for word in sections)]
        docs = matching or docs
    return docs


def _source(doc):
    return {"document_id": doc.metadata.get("document_id"), "document_name": doc.metadata.get("document_name", "Document"), "page": doc.metadata.get("page"), "section": doc.metadata.get("section", "Unknown")}


def _answer_individual_question(question, document_ids):
    ids, error = _validate_document_ids(document_ids)
    if error:
        return {"success": False, "message": error}
    vectorstore = _open_vectorstore()
    contexts = []
    sources = []
    for document_id in ids:
        docs = _retrieve(vectorstore, document_id, question, k=5, fetch_k=12)
        if not docs:
            continue
        name = docs[0].metadata.get("document_name", document_id)
        contexts.extend([f"DOCUMENT: {name}\nPAGE {d.metadata.get('page', 'Unknown')} ({d.metadata.get('section', 'Unknown')}):\n{d.page_content}" for d in docs])
        sources.extend(_source(d) for d in docs)
    if not contexts:
        return {"success": False, "message": "I could not find relevant information in the selected PDFs."}
    prompt = f"""You are a document assistant. Answer using ONLY the provided document content. Do not invent facts; say clearly when information is not present. Mention page numbers when useful. Attribute each statement to its specific document. Compare documents when asked, and state when a fact appears in only some documents.

DOCUMENT CONTENT:\n\n{'\n\n'.join(contexts)}

QUESTION:\n{question}"""
    response = invoke_with_retry(load_llm(), prompt)
    return {"success": True, "answer": response.content, "sources": sources}


def answer_individual_question(question, document_ids):
    try:
        return _answer_individual_question(question, document_ids if isinstance(document_ids, list) else [document_ids])
    except Exception as error:
        if is_rate_limit_error(error):
            return {"success": False, "message": "The AI service is busy right now (rate limit). Please wait a minute and try again."}
        raise


def _summary_for_document(vectorstore, document_id):
    result = vectorstore.get(where={"document_id": document_id}, include=["documents", "metadatas"])
    rows = [{"page": (meta or {}).get("page", 0), "chunk_id": (meta or {}).get("chunk_id", ""), "section": (meta or {}).get("section", "Unknown"), "document_name": (meta or {}).get("document_name", "Document"), "content": content} for content, meta in zip(result.get("documents", []), result.get("metadatas", []))]
    rows.sort(key=lambda row: (row["page"], row["chunk_id"]))
    if not rows:
        return None, []
    batches, current, size = [], [], 0
    for row in rows:
        block = f"Page {row['page']} ({row['section']}):\n{row['content']}"
        while len(block) > MAX_SUMMARY_CHARACTERS:
            if current:
                batches.append("\n\n".join(current)); current, size = [], 0
            batches.append(block[:MAX_SUMMARY_CHARACTERS])
            block = block[MAX_SUMMARY_CHARACTERS:]
        if size + len(block) > MAX_SUMMARY_CHARACTERS and current:
            batches.append("\n\n".join(current)); current, size = [], 0
        current.append(block); size += len(block) + 2
    if current:
        batches.append("\n\n".join(current))
    llm = load_llm()
    partials = []
    for index, batch in enumerate(batches):
        prompt = f"Summarize this segment of a document faithfully, preserving its claims, methods, findings, limitations, and page references. Use ONLY its content; do not invent and identify missing details clearly. Segment {index + 1} of {len(batches)}:\n\n{batch}"
        partials.append(str(invoke_with_retry(llm, prompt).content))
        if index + 1 < len(batches):
            time.sleep(2)
    final_prompt = """Combine the following ordered segment summaries into one structured whole-document summary with sections: Main topic and purpose, Key concepts, Methodology, Findings/results, Arguments, Limitations, Conclusion, Key takeaways. Cover the full document including its ending. Use ONLY the supplied summaries, do not invent, and mention page numbers when useful. If something is not stated, say so clearly.\n\n""" + "\n\n".join(partials)
    answer = invoke_with_retry(llm, final_prompt).content
    return answer, [_source(Document(page_content="", metadata={**row, "document_id": document_id})) for row in rows]


def _run_action_for_document(vectorstore, action, document_id):
    if action == "summary":
        return _summary_for_document(vectorstore, document_id)
    query_sections = {
        "objective": ("abstract introduction background purpose objective aim conclusion", ["abstract", "introduction", "background", "conclusion"], 14),
        "findings": ("results findings evaluation discussion conclusion outcomes", ["results", "evaluation", "discussion", "conclusion"], 12),
        "methodology": ("methods methodology approach experiments procedure data analysis", ["method", "approach", "experiment", "procedure"], 12),
    }
    query, section_terms, k = query_sections[action]
    docs = _retrieve(vectorstore, document_id, query, k=k, fetch_k=max(k * 2, 24), sections=section_terms)
    if not docs:
        return None, []
    name = docs[0].metadata.get("document_name", document_id)
    context = "\n\n".join(f"Page {d.metadata.get('page')} ({d.metadata.get('section', 'Unknown')}):\n{d.page_content}" for d in docs)
    instructions = {
        "objective": "Explain what the document is trying to achieve and why, using abstract, introduction, background, or conclusion evidence.",
        "findings": "Return the key findings as concise bullets, including numbers where present and citing pages.",
        "methodology": "Explain the methodology or approach step by step, citing pages.",
    }
    prompt = f"You are analyzing {name}. {instructions[action]} Use ONLY the provided document content, do not invent, clearly state when something is not in the document, and mention page numbers when useful.\n\nDOCUMENT CONTENT:\n{context}"
    return invoke_with_retry(load_llm(), prompt).content, [_source(d) for d in docs]


def run_individual_action(action, document_ids):
    try:
        if action not in {"summary", "objective", "findings", "methodology"}:
            return {"success": False, "message": "Unknown document action."}
        ids, error = _validate_document_ids(document_ids)
        if error:
            return {"success": False, "message": error}
        vectorstore = _open_vectorstore()
        sections, sources = [], []
        for index, document_id in enumerate(ids):
            result, docs = _run_action_for_document(vectorstore, action, document_id)
            if not result:
                name = os.path.basename(get_pdf_path(document_id))
                sections.append(f"## {name}\n\nNo indexed content was found for this document.")
            else:
                name = docs[0].get("document_name", document_id) if docs else document_id
                sections.append(f"## {name}\n\n{result}")
                sources.extend(docs)
            if index + 1 < len(ids):
                time.sleep(2)
        if action == "summary" and len(ids) > 1:
            time.sleep(2)
            cross_prompt = "Compare these document summaries. Briefly describe common themes and differences, using ONLY the summaries and not inventing details.\n\n" + "\n\n".join(sections)
            cross = invoke_with_retry(load_llm(), cross_prompt).content
            sections.append(f"## ACROSS DOCUMENTS\n\n{cross}")
        return {"success": True, "answer": "\n\n".join(sections), "sources": sources}
    except Exception as error:
        if is_rate_limit_error(error):
            return {"success": False, "message": "The AI service is busy right now (rate limit). Please wait a minute and try again."}
        raise


