# Retrieve.py
from typing import List, Dict
import numpy as np
from Database_Handler import load_all, msearch, embed_query
 
# --------------------------
# Search function with scores
# --------------------------
def search(query_text: str, top_k: int = 5) -> List[Dict]:
    """
    Search FAISS index using a query text, return top-k results with scores.
    Each result contains: 'source', 'path', 'text', 'score'.
    """
    if not query_text.strip():
        return []
 
    # Embed query
    try:
        query_vector = embed_query(query_text)
    except Exception as e:
        print(f"Failed to embed query: {e}")
        return []
 
    query_vector = np.array(query_vector, dtype=np.float32).reshape(1, -1)
 
    # Load FAISS index
    index, meta = load_all()
    if index is None or len(meta) == 0:
        return []
 
    # Normalize for cosine similarity
    from faiss import normalize_L2
    normalize_L2(query_vector)
 
    # Search
    D, I = index.search(query_vector, top_k)
    results: List[Dict] = []
    for score, i in zip(D[0], I[0]):
        if 0 <= i < len(meta):
            r = meta[i].copy()
            r["score"] = float(score)
            results.append(r)
    return results
 
# --------------------------
# Build context function
# --------------------------
def build_context(results: List[Dict], max_chars: int = 2000) -> str:
    """
    Build structured context grouped by module/document.
    Helps LLM see natural flows across layers.
    """
    if not results:
        return ""
 
    context: List[str] = []
    grouped: Dict[str, List[str]] = {}
    for r in results:
        source = r.get("source", "Unknown")
        text = r.get("text", "")
        grouped.setdefault(source, []).append(text)
 
    for module, texts in grouped.items():
        context.append(f"### {module}\n")
        for t in texts:
            context.append(t[:max_chars])  # truncate per chunk
    return "\n".join(context)