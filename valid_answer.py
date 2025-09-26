import os
import pickle
import numpy as np
from typing import List, Dict
from Data_Handler import embed_texts, embed_query
import config

GOOD_FILE = os.path.join("data", "good_answers.csv")
EMB_CACHE_FILE = os.path.join("vector_store", "good_embeddings_cache.pkl")

# --------------------------
# Load good answers
# --------------------------
if os.path.exists(GOOD_FILE):
    import pandas as pd
    try:
        df_good = pd.read_csv(GOOD_FILE, on_bad_lines='skip')
    except pd.errors.EmptyDataError:
        df_good = pd.DataFrame(columns=["question", "answer"])
else:
    import pandas as pd
    df_good = pd.DataFrame(columns=["question", "answer"])

# Ensure columns exist
for col in ["question", "answer"]:
    if col not in df_good.columns:
        df_good[col] = ""

# --------------------------
# Embedding cache for good answers
# --------------------------
if os.path.exists(EMB_CACHE_FILE):
    with open(EMB_CACHE_FILE, "rb") as f:
        emb_cache = pickle.load(f)
else:
    emb_cache = {}

def cached_embed(text: str):
    if text in emb_cache:
        return emb_cache[text]
    emb = embed_query(text)
    emb_cache[text] = emb
    with open(EMB_CACHE_FILE, "wb") as f:
        pickle.dump(emb_cache, f)
    return emb

# --------------------------
# Add a good answer
# --------------------------
def add_good_answer(question: str, answer: str):
    global df_good
    df_good = pd.concat([df_good, pd.DataFrame([{"question": question, "answer": answer}])], ignore_index=True)
    df_good.to_csv(GOOD_FILE, index=False)
    # Also update embedding cache
    cached_embed(question)

# --------------------------
# Search good answers by similarity
# --------------------------
def search_good_answer(query: str, top_k: int = 3, threshold: float = 0.8) -> List[Dict]:
    """
    Return top_k good answers based on cosine similarity.
    """
    if df_good.empty:
        return []

    query_vec = cached_embed(query)  # normalized vector

    # Prepare embeddings matrix for all good answers
    good_questions = df_good["question"].tolist()
    good_embeddings = np.array([cached_embed(q) for q in good_questions], dtype=np.float32)

    # Normalize embeddings
    query_vec_norm = query_vec / np.linalg.norm(query_vec)
    good_emb_norm = good_embeddings / np.linalg.norm(good_embeddings, axis=1, keepdims=True)

    # Cosine similarity
    sims = good_emb_norm @ query_vec_norm
    top_indices = sims.argsort()[::-1][:top_k]

    results = []
    for i in top_indices:
        if sims[i] >= threshold:
            results.append({
                "question": df_good.iloc[i]["question"],
                "answer": df_good.iloc[i]["answer"],
                "score": float(sims[i])
            })
    return results
