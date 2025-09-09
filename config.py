#  config.py
from dotenv import load_dotenv
import os
from pathlib import Path

# ----------------------------
# Load .env file
# ----------------------------
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# ----------------------------
# OpenAI API Key
# ----------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found. Check your .env file!")

# ----------------------------
# RAG / Document processing settings
# ----------------------------
TOP_K = 5                # Number of top chunks to retrieve for a query
CHUNK_SIZE = 1000        # Number of characters per chunk when splitting text
CHUNK_OVERLAP = 200      # Number of overlapping characters between chunks

# ----------------------------
# Vector DB / Embedding settings
# ----------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Model for embeddings
VECTOR_DIM = 384  # Dimensionality of the embedding vectors (matches model output)

# ----------------------------
# LLM / OpenAI settings
# ----------------------------
LLM_MODEL = "gpt-4o-mini"  # Model to use for generating answers
TEMPERATURE = 0             # Deterministic answers
MAX_TOKENS = 500            # Max tokens in response

# ----------------------------
# Other optional settings
# ----------------------------
PDF_PATH = "/home/sweng-06/Documents/AUTOSAR_SWS_PDURouter 4.4.0.pdf"  # Default PDF


