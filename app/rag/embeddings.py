# app/rag/embeddings.py
"""
Embedding generation service.
"""

from typing import List, Union
from langchain_openai import OpenAIEmbeddings
# from langchain_community.embeddings import HuggingFaceEmbeddings  # For local fallback

from app.core.config import settings


from app.core.ai_models import get_embeddings as _get_embeddings

def get_embedding_model():
    """
    Get the configured embedding model.
    Delegates to Centralized AI Configuration.
    """
    return _get_embeddings()
    
    # FUTURE: Add local fallback if requested
    # return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
