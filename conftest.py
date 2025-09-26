import os
import pytest
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
import config  # import your config.py

API_KEY = getattr(config, "OPENAI_API_KEY", None)
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in config.py")

# ---------------------------
# Fixtures for pytest
# ---------------------------

@pytest.fixture(scope="session")
def langchain_llm_ragas_wrapper():
    """
    Fixture: Provides an LLM wrapper for RAGAS metrics
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=API_KEY)
    return LangchainLLMWrapper(llm)


@pytest.fixture(scope="session")
def get_embeddings():
    """
    Fixture: Provides an embeddings wrapper for RAGAS metrics
    """
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key=API_KEY)
    return LangchainEmbeddingsWrapper(embeddings)
