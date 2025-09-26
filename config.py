import os
from dotenv import load_dotenv
from RAG_prompt import RAG_SYSTEM_PROMPT
 
# Load .env file
load_dotenv()
 
# Required
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set. Put it in .env or environment.")
 
# Models
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large").strip()
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini").strip()
 
# Vector DB
DB_DIR = os.getenv("DB_DIR", "vector_store").strip()
COLLECTION = os.getenv("COLLECTION", "autosar").strip()
 
# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "4800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "550"))
MAX_CHUNKS_PER_FILE = int(os.getenv("MAX_CHUNKS_PER_FILE", "4000"))
TOP_K = int(os.getenv("TOP_K", "200"))
 
# Safety/guardrails (RAG prompt template)
SYSTEM_PROMPT = RAG_SYSTEM_PROMPT
 
# Feedback
FEEDBACK_CSV = os.getenv("FEEDBACK_CSV", "feedback.csv").strip()
 
# -------------------------------
# ✅ Added for deterministic RAG
# -------------------------------
 
# Force deterministic output (no randomness across users)
TEMPERATURE = float(os.getenv("TEMPERATURE", "0"))
 
# Minimum similarity for FAISS retrieval
# If below threshold → "No match found in AUTOSAR docs"
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))