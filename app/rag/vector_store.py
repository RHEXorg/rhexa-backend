# app/rag/vector_store.py
"""
Vector Store Management (FAISS).

Handles:
- Indexing documents with per-organization isolation
- MMR (Maximal Marginal Relevance) retrieval for diverse, high-quality results
- Thread-safe concurrent access
- Lazy initialization (no dummy init document polluting the index)
"""

import os
import logging
import threading
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document as LangChainDocument

from app.core.config import settings
from app.rag.embeddings import get_embedding_model

logger = logging.getLogger(__name__)


class LockManager:
    """Thread-safe per-organization locks."""

    def __init__(self):
        self._locks: Dict[int, threading.Lock] = {}
        self._global_lock = threading.Lock()

    def get_lock(self, organization_id: int) -> threading.Lock:
        with self._global_lock:
            if organization_id not in self._locks:
                self._locks[organization_id] = threading.Lock()
            return self._locks[organization_id]


vector_locks = LockManager()


class VectorStoreManager:
    """
    Manages FAISS vector stores for multiple organizations.
    One isolated index per organization.
    """

    def __init__(self):
        self.base_path = Path(settings.VECTOR_DB_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._embeddings = None
        # In-memory cache: org_id → FAISS instance
        self._cache: Dict[int, FAISS] = {}
        self._cache_lock = threading.Lock()

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = get_embedding_model()
        return self._embeddings

    def _get_org_path(self, organization_id: int) -> str:
        org_path = self.base_path / f"org_{organization_id}"
        return str(org_path)

    def _load_from_disk(self, path: str) -> Optional[FAISS]:
        """Load FAISS index from disk. Returns None if not found or corrupt."""
        index_file = os.path.join(path, "index.faiss")
        if not os.path.exists(index_file):
            return None
        try:
            # Try with the modern security flag
            return FAISS.load_local(
                folder_path=path,
                embeddings=self.embeddings,
                allow_dangerous_deserialization=True
            )
        except TypeError:
            # Fallback for older LangChain versions that don't use this flag
            try:
                return FAISS.load_local(
                    folder_path=path,
                    embeddings=self.embeddings
                )
            except Exception as e:
                logger.error(f"Fallback load failed. FAISS index at {path} might be corrupt: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to load FAISS index at {path}: {e}")
            return None

    def get_vector_store(self, organization_id: int) -> Optional[FAISS]:
        """
        Get vector store for an organization.
        Uses in-memory cache; falls back to disk load; returns None if not yet indexed.
        """
        with self._cache_lock:
            if organization_id in self._cache:
                return self._cache[organization_id]

        path = self._get_org_path(organization_id)
        store = self._load_from_disk(path)

        if store is not None:
            logger.info(f"Successfully loaded FAISS index for org {organization_id} from {path}")
            with self._cache_lock:
                self._cache[organization_id] = store
        else:
            logger.warning(f"No FAISS index found on disk for org {organization_id} at {path}")

        return store

    def add_documents(self, organization_id: int, documents: List[LangChainDocument]):
        """
        Add document chunks to the organization's FAISS index.
        Thread-safe. Updates both disk and in-memory cache.
        """
        if not documents:
            logger.warning(f"add_documents called with empty list for org {organization_id}")
            return

        lock = vector_locks.get_lock(organization_id)
        with lock:
            path = self._get_org_path(organization_id)
            os.makedirs(path, exist_ok=True)

            existing = self._load_from_disk(path)

            if existing is not None:
                existing.add_documents(documents)
                vector_store = existing
            else:
                # First-time creation — no dummy doc needed
                vector_store = FAISS.from_documents(documents, self.embeddings)

            vector_store.save_local(path)

            # Update in-memory cache
            with self._cache_lock:
                self._cache[organization_id] = vector_store

            logger.info(
                f"Indexed {len(documents)} chunks for org {organization_id} → {path}"
            )

    def delete_document(self, organization_id: int, document_id: int):
        """
        Remove all chunks belonging to a specific document from the index.
        """
        lock = vector_locks.get_lock(organization_id)
        with lock:
            path = self._get_org_path(organization_id)
            store = self._load_from_disk(path)
            if store is None:
                return

            ids_to_delete = [
                internal_id
                for internal_id, doc in store.docstore._dict.items()
                if doc.metadata.get("document_id") == document_id
            ]

            if ids_to_delete:
                store.delete(ids_to_delete)
                store.save_local(path)
                # Invalidate cache
                with self._cache_lock:
                    self._cache.pop(organization_id, None)
                logger.info(
                    f"Deleted {len(ids_to_delete)} vectors for doc {document_id} "
                    f"(org {organization_id})"
                )
            else:
                logger.warning(
                    f"No vectors found for document {document_id} in org {organization_id}"
                )

    def search_mmr(
        self,
        organization_id: int,
        query: str,
        k: int = 15,
        fetch_k: int = 60,
        lambda_mult: float = 0.65,
        document_ids: List[int] = None,
    ) -> List[Tuple[LangChainDocument, float]]:
        """
        Reliable similarity search with Python-side post-filtering.

        Strategy:
        - Fetch a very large pool from FAISS (no filter= param, unreliable in many LangChain versions)
        - Filter by document_id in Python after retrieval
        - Sort by score and return top-k
        """
        store = self.get_vector_store(organization_id)
        if store is None:
            logger.warning(f"[RAG] No FAISS store for org {organization_id}")
            return []

        doc_ids_set = set(document_ids) if document_ids else None
        logger.info(f"[RAG Search] Org={organization_id} | DocFilter={doc_ids_set} | Query='{query[:60]}'")

        # When filtering, fetch MUCH more to compensate for post-filter reduction
        if doc_ids_set:
            big_k = min(500, max(200, k * 25))
        else:
            big_k = max(80, fetch_k)

        try:
            # Step 1: Broad similarity search — no filter param (most compatible)
            all_results = store.similarity_search_with_score(query, k=big_k)
            logger.info(f"[RAG Search] Raw FAISS results: {len(all_results)}")

            if not all_results:
                logger.warning(f"[RAG Search] FAISS returned 0 results for org {organization_id}")
                return []

            # Step 2: Python-side filter by document_id
            if doc_ids_set:
                filtered = [
                    (doc, score) for doc, score in all_results
                    if doc.metadata.get("document_id") in doc_ids_set
                ]
                logger.info(
                    f"[RAG Search] After filter: {len(filtered)} results "
                    f"(doc_ids in store: {set(d.metadata.get('document_id') for d, _ in all_results)})"
                )
                if not filtered:
                    # Doc_ids don't match anything — files likely not re-indexed after upload
                    # Fall back to all results so AI can still attempt to answer
                    logger.warning("[RAG Search] Filter matched nothing — using unfiltered results as fallback")
                    filtered = all_results
            else:
                filtered = all_results

            # Step 3: Sort by score ascending (lower = more similar in L2/cosine)
            filtered.sort(key=lambda x: x[1])

            # Step 4: Return top-k
            final = filtered[:k]
            logger.info(f"[RAG Search] Returning {len(final)} chunks to LLM")
            return final

        except Exception as e:
            logger.error(f"[RAG Search] Exception for org {organization_id}: {e}", exc_info=True)
            return []


# Global singleton
vector_store_manager = VectorStoreManager()


def get_vector_store(organization_id: int) -> Optional[FAISS]:
    return vector_store_manager.get_vector_store(organization_id)
