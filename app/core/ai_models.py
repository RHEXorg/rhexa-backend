# app/core/ai_models.py
"""
Centralized AI Model Configuration. 

Use this file to switch between different AI providers (OpenAI, Ollama, OpenRouter, etc.).
Just uncomment the section you want to use and comment out the others.
"""

import warnings
import os
from app.core.config import settings

# Suppress all warnings
warnings.filterwarnings('ignore')

# Suppress HuggingFace progress bars and info messages
os.environ['HF_HUB_DISABLE_PROGRESSBARS'] = '1'
os.environ['HF_HUB_DISABLE_SYMLINKS'] = '1'
os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['VERBOSITY'] = 'error'
if hasattr(settings, 'HF_TOKEN') and settings.HF_TOKEN:
    os.environ['HF_TOKEN'] = settings.HF_TOKEN

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# from langchain_community.chat_models import ChatOllama
# from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.embeddings import FakeEmbeddings

# ==============================================================================
# 1. LLM CONFIGURATION (Chat Model)
# ==============================================================================

_llm_cache = None

def get_llm():
    """
    Returns the configured Language Model (LLM).
    Prioritizes OpenRouter, then OpenAI. Caches result.
    """
    global _llm_cache
    if _llm_cache:
        return _llm_cache
    
    # ... logic ...
    res = None
    
    if settings.OPENROUTER_API_KEY:
        res = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.OPENROUTER_MODEL,
            temperature=0
        )
    elif settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-change-this"):
        res = ChatOpenAI(
            model="gpt-3.5-turbo",
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0
        )
    
    _llm_cache = res
    return res


# ==============================================================================
# 2. EMBEDDING CONFIGURATION (Vector Conversions)
# ==============================================================================

_embeddings_cache = None

def get_embeddings():
    """
    Returns the configured Embedding Model.
    Must match the dimensions of your Vector DB! Caches result.
    """
    global _embeddings_cache
    if _embeddings_cache:
        return _embeddings_cache

    res = None

    # ------------------------------------------------------------------
    # OPTION A: OpenAI Embeddings (1536 dimensions) - DEFAULT
    # ------------------------------------------------------------------
    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-change-this"):
        res = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL, 
            openai_api_key=settings.OPENAI_API_KEY
        )
    else:
        import logging
        # Silence transformers logs before loading
        logging.getLogger("transformers").setLevel(logging.ERROR)
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
        
        logger = logging.getLogger(__name__)
        logger.info("Using HuggingFace local embeddings (all-MiniLM-L6-v2) for RAG.")
        from langchain_community.embeddings import HuggingFaceEmbeddings
        res = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    _embeddings_cache = res
    return res
