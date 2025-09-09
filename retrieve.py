# Retrieve top-k chunks for a query

from data_handler import model

def retrieve_top_k(db, query, top_k):
    query_embedding = model.encode([query])[0]
    return db.search(query_embedding, top_k)