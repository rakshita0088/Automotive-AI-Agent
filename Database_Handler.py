import os
import faiss
import numpy as np
import pickle
from typing import List, Dict, Tuple
 
from Document_Handler import load_document, load_arxml  # ARXML loader
from Data_Handler import chunk_text, embed_texts, embed_query
import config
 
DB_DIR = config.DB_DIR
FAISS_INDEX_PATH = os.path.join(DB_DIR, f"{config.COLLECTION}.faiss")
META_PATH = os.path.join(DB_DIR, f"{config.COLLECTION}_meta.pkl")
 
# --------------------------
# Helper functions
# --------------------------
def _ensure_dir():
    os.makedirs(DB_DIR, exist_ok=True)
 
def create_or_load_index(d: int) -> Tuple[faiss.IndexFlatIP, List[Dict]]:
    """Create new FAISS index or load existing one."""
    _ensure_dir()
    if os.path.exists(FAISS_INDEX_PATH) and os.path.exists(META_PATH):
        index = faiss.read_index(FAISS_INDEX_PATH)
        with open(META_PATH, "rb") as f:
            meta = pickle.load(f)
        return index, meta
    else:
        index = faiss.IndexFlatIP(d)  # cosine similarity
        return index, []
 
def save_index(index: faiss.IndexFlatIP, meta: List[Dict]):
    _ensure_dir()
    faiss.write_index(index, FAISS_INDEX_PATH)
    with open(META_PATH, "wb") as f:
        pickle.dump(meta, f)
 
# --------------------------
# Add chunks to FAISS
# --------------------------
def add_text_chunks(chunks: List[str], embeddings: List[List[float]], source_name: str, source_path: str) -> int:
    """Add text chunks + embeddings to FAISS index."""
    if not chunks:
        return 0
 
    d = len(embeddings[0])
    index, meta = create_or_load_index(d)
 
    # Normalize embeddings for cosine similarity
    xb = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(xb)
    index.add(xb)
 
    # Update metadata
    for text in chunks:
        meta.append({
            "source": source_name,
            "path": source_path,
            "text": text
        })
 
    save_index(index, meta)
    return len(chunks)
 
# --------------------------
# Semantic search
# --------------------------
def msearch(query: str, top_k: int = 5) -> List[Dict]:
    """Search FAISS index for top_k relevant chunks."""
    try:
        query_vector = embed_query(query)
    except Exception as e:
        print(f"Failed to embed query: {e}")
        return []
 
    d = len(query_vector)
    index, meta = create_or_load_index(d)
 
    if len(meta) == 0:
        return []
 
    # Normalize query
    q = np.array(query_vector, dtype=np.float32).reshape(1, -1)
    faiss.normalize_L2(q)
 
    # Search
    D, I = index.search(q, top_k)
    results = []
    for score, i in zip(D[0], I[0]):
        if 0 <= i < len(meta):
            r = meta[i].copy()
            r["score"] = float(score)
            results.append(r)
    return results
 
# --------------------------
# Load entire FAISS index
# --------------------------
def load_all() -> Tuple[faiss.IndexFlatIP, List[Dict]]:
    """Return index and metadata if exists, else (None, [])."""
    if not os.path.exists(FAISS_INDEX_PATH) or not os.path.exists(META_PATH):
        return None, []
    index = faiss.read_index(FAISS_INDEX_PATH)
    with open(META_PATH, "rb") as f:
        meta = pickle.load(f)
    return index, meta
 
# --------------------------
# Ingest documents
# --------------------------
def ingest_documents(paths: List[str]) -> int:
    """Load documents (PDF, DOCX, MD, etc.), chunk, embed, and add to FAISS."""
    total_chunks = 0
    for path in paths:
        try:
            doc = load_document(path)
            text = doc.get("content", "")
            chunks = chunk_text(text)
            embeddings = embed_texts(chunks)
            added = add_text_chunks(chunks, embeddings, source_name=doc.get("name", ""), source_path=path)
            total_chunks += added
        except Exception as e:
            print(f"Failed to ingest {path}: {e}")
    return total_chunks
 
# --------------------------
# Ingest ARXML files
# --------------------------
def ingest_arxml_files(paths: List[str]) -> int:
    """Specifically ingest ARXML files into FAISS."""
    total_chunks = 0
    for path in paths:
        ext = os.path.splitext(path)[1].lower()
        if ext != ".arxml":
            continue
        try:
            doc = load_arxml(path)
            chunks = chunk_text(" ".join([c["text"] for c in doc["chunks"]]))
            embeddings = embed_texts(chunks)
            added = add_text_chunks(chunks, embeddings, source_name=doc.get("name", ""), source_path=path)
            total_chunks += added
        except Exception as e:
            print(f"Failed to ingest ARXML {path}: {e}")
    return total_chunks
 
 