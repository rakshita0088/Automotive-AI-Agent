from typing import List, Dict
import re
from openai import OpenAI
import config
import tiktoken
import time
import hashlib
 
# --------------------------
# OpenAI client
# --------------------------
_client = OpenAI(api_key=config.OPENAI_API_KEY)
 
# --------------------------
# Tokenizer helper
# --------------------------
def chunk_by_tokens(text: str, max_tokens: int, model: str) -> List[str]:
    """Split a text chunk into smaller chunks that fit within max_tokens."""
    enc = tiktoken.encoding_for_model(model)
    tokens = enc.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        chunks.append(chunk_text)
        start = end
    return chunks
 
# --------------------------
# Heading-based chunking
# --------------------------
def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
 
def _heading_split(text: str) -> List[str]:
    pattern = r"(?=\n#{1,6} .*|\n\d+(\.\d+)* .*|\n[A-Z][^\n]+\n[-=]{3,})"
    parts = re.split(pattern, text)
    chunks = []
    buffer = ""
    for part in parts:
        if not part or part.isspace():
            continue
        if re.match(pattern, "\n" + part):
            if buffer:
                chunks.append(buffer.strip())
                buffer = ""
        buffer += part.strip() + " "
    if buffer:
        chunks.append(buffer.strip())
    return chunks
 
def chunk_text(text: str, chunk_type: str = "paragraph") -> List[str]:
    """
    Heading-based chunking with token splitting.
    chunk_type can be 'paragraph', 'figure', 'message', 'signal', 'cdd_element', 'arxml_element'
    """
    text = _normalize_ws(text)
    if not text:
        return []
 
    heading_chunks = _heading_split(text) if chunk_type == "paragraph" else [text]
 
    max_tokens = getattr(config, "CHUNK_SIZE", 500)
    if chunk_type == "figure":
        max_tokens = min(max_tokens, 150)
    elif chunk_type in ["message", "signal"]:
        max_tokens = min(max_tokens, 200)
    elif chunk_type in ["cdd_element"]:
        max_tokens = min(max_tokens, 180)
    elif chunk_type == "arxml_element":
        max_tokens = min(max_tokens, 200)
 
    safe_chunks = []
    for chunk in heading_chunks:
        token_chunks = chunk_by_tokens(chunk, max_tokens, config.EMBED_MODEL)
        safe_chunks.extend(token_chunks)
 
    max_chunks = getattr(config, "MAX_CHUNKS_PER_FILE", len(safe_chunks))
    if len(safe_chunks) > max_chunks:
        safe_chunks = safe_chunks[:max_chunks]
 
    return safe_chunks
 
# --------------------------
# Embedding helpers
# --------------------------
def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed multiple text chunks deterministically."""
    embeddings = []
    for chunk in texts:
        # Use SHA256 hash as deterministic cache key
        key = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
        # Call API
        resp = _client.embeddings.create(input=chunk, model=config.EMBED_MODEL)
        emb = resp.data[0].embedding
        embeddings.append(emb)
        time.sleep(0.1)
    return embeddings
 
def embed_query(query: str) -> List[float]:
    """Embed a single query deterministically."""
    resp = _client.embeddings.create(input=query, model=config.EMBED_MODEL)
    return resp.data[0].embedding
 
# --------------------------
# Process structured chunks from Document_Handler
# --------------------------
def process_document_chunks(chunks: List[Dict]) -> List[str]:
    """
    Flatten structured document chunks (paragraph, figure, message, signal, cdd_element, arxml_element)
    into text chunks ready for embedding.
    """
    final_chunks = []
    for c in chunks:
        ctype = c.get("type", "paragraph")
        if ctype == "figure_text":
            final_chunks.extend(chunk_text(c["text"], chunk_type="figure"))
        elif ctype in ["message", "signal", "cdd_element"]:
            final_chunks.extend(chunk_text(c["text"], chunk_type=ctype))
        elif ctype == "arxml_element":
            final_chunks.extend(chunk_text(c["text"], chunk_type="arxml_element"))
        else:
            final_chunks.extend(chunk_text(c["text"], chunk_type="paragraph"))
    return final_chunks
 

