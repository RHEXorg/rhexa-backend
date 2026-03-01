import logging
logging.basicConfig(level=logging.INFO)

from app.rag.vector_store import vector_store_manager

# Replace 1 with the user's actual organization ID if known, 
# or just test with a common one we might find in DB.
org_id = 1 
try:
    results = vector_store_manager.search_mmr(
        organization_id=org_id,
        query="test",
        k=5,
        fetch_k=20,
        document_ids=None
    )
    print("RESULTS:", results)
except Exception as e:
    print("ERROR:", e)
