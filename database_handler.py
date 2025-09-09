# Use FAISS to store and search embeddings

import faiss
import numpy as np

class VectorDB:
    def __init__(self, dimension):
        self.index = faiss.IndexFlatL2(dimension)
        self.text_chunks = []

    def add_chunks(self, embeddings, chunks):
        embeddings = np.array(embeddings, dtype="float32")
        self.index.add(embeddings)
        self.text_chunks.extend(chunks)

    def search(self, query_embedding, top_k=5):
        query_embedding = np.array([query_embedding], dtype="float32")
        distances, indices = self.index.search(query_embedding, top_k)
        return [self.text_chunks[i] for i in indices[0]]
