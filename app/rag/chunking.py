# app/rag/chunking.py
"""
Intelligent text chunking for RAG.

Strategy:
- Larger chunks (1500 chars) = more context per chunk = LLM sees full paragraphs
- Higher overlap (300 chars) = ideas that span chunk boundaries are not lost
- Sentence-aware splitting: tries to break at paragraphs → sentences → words → chars
"""

from typing import List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument
from app.core.config import settings


def split_text(text: str, metadata: dict = None) -> List[LangChainDocument]:
    """
    Split text into overlapping, semantically meaningful chunks.

    Uses RecursiveCharacterTextSplitter which respects natural boundaries:
      1. Paragraph breaks (\\n\\n)
      2. Sentence ends (. ! ?)
      3. Newlines (\\n)
      4. Spaces / character fallback

    Args:
        text: Raw text to split
        metadata: Optional metadata to attach to every chunk

    Returns:
        List of LangChain Document objects
    """
    if not text or not text.strip():
        return []

    # Use config values but enforce smarter minimums
    chunk_size = max(settings.CHUNK_SIZE, 1500)
    chunk_overlap = max(settings.CHUNK_OVERLAP, 300)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # Sentence-aware separators — tries each in order
        separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
        length_function=len,
        is_separator_regex=False,
    )

    safe_meta = metadata or {}

    chunks = splitter.create_documents(
        texts=[text],
        metadatas=[safe_meta]
    )

    # Attach chunk index for debugging / citation ordering
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i
        chunk.metadata["total_chunks"] = len(chunks)

    return chunks
