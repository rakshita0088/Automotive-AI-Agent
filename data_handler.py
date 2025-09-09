# Chunk text and create embeddings

import numpy as np
from sentence_transformers import SentenceTransformer
from config import CHUNK_SIZE, CHUNK_OVERLAP

# Load the embedding model once here
embedder = SentenceTransformer("all-MiniLM-L6-v2")

def chunk_text(text):
    """
    Break text into overlapping chunks
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def embed_chunks(chunks):
    """
    Convert text chunks to embeddings (float32)
    """
    embeddings = embedder.encode(chunks, convert_to_numpy=True)
    return np.array(embeddings, dtype="float32")
