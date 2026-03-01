import os
import sys

# Setup imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.document import Document
from app.rag.vector_store import get_vector_store
from app.rag.embeddings import get_embedding_model

def debug():
    db = SessionLocal()
    doc = db.query(Document).first()
    if not doc:
        print("No document found.")
        return
        
    print(f"Document: {doc.filename}")
    
    org_id = doc.organization_id
    print(f"Loading vector store for org {org_id}...")
    store = get_vector_store(org_id)
    
    # Let's count the number of chunks inside FAISS
    if store and hasattr(store, 'index'):
        count = store.index.ntotal
        print(f"Total vectors stored in FAISS: {count}")
    else:
        print("Could not access FAISS index!")
        return

    # Let's see what a query returns
    query = "employee in new york"
    results = store.similarity_search_with_score(query, k=5)
    
    print("\nSearch Results for 'employee in new york':")
    for doc, score in results:
        text = doc.page_content.replace('\n', ' ')[:150]
        snippet = f"[{score:.4f}] {text}..."
        print(snippet)

if __name__ == '__main__':
    debug()
