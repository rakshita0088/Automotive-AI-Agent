# Handle queries from UI or CLI

from data_handler import embedder  # 👈 import from data_handler
from llm_handler import generate_answer
from config import TOP_K

def answer_query(vector_db, query):
    """
    Embed query, search DB, and ask LLM for answer
    """
    query_embedding = embedder.encode(query, convert_to_numpy=True).astype("float32")
    relevant_chunks = vector_db.search(query_embedding, top_k=TOP_K)
    answer = generate_answer(relevant_chunks, query)
    return answer

