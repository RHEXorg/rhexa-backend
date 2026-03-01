import os
import sys
import shutil

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.document import Document
from app.services.rag_service import index_document
from app.core.storage import LocalStorage
from app.ingestion.loader import load_file

from app.core.config import settings

def rebuild():
    # Nuke existing vectors to prevent dimension mismatch (Fake=1536 vs HF=384)
    vectors_dir = settings.VECTOR_DB_PATH
    if os.path.exists(vectors_dir):
        print(f"Nuking old vectors at {vectors_dir}...")
        shutil.rmtree(vectors_dir)
        os.makedirs(vectors_dir, exist_ok=True)
        
    db = SessionLocal()
    storage = LocalStorage()
    
    docs = db.query(Document).all()
    print(f"Found {len(docs)} documents to re-index...")
    
    for doc in docs:
        try:
            print(f"Re-indexing {doc.filename}...")
            full_path = storage.get_full_path(doc.file_path)
            extracted_text = load_file(full_path, organization_id=doc.organization_id)
            index_document(db, doc, extracted_text)
            print(f"Successfully re-indexed {doc.filename}")
        except Exception as e:
            print(f"Failed to index {doc.filename}: {e}")

if __name__ == '__main__':
    rebuild()
