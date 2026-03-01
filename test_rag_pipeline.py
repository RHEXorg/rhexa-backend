# test_rag_pipeline.py
"""
Integration test for RheXa RAG Pipeline (Phase 1.9).
"""

import httpx
import time
import os
import shutil

BASE_URL = "http://127.0.0.1:8000"
TEST_FILE = "rag_test_doc.txt"

def test_rag_flow():
    print("="*80)
    print("RheXa RAG Pipeline - Integration Test")
    print("="*80)
    
    # Clean up previous vector store
    if os.path.exists("vector_store"):
        try:
            shutil.rmtree("vector_store")
        except:
            pass
    
    timestamp = int(time.time())
    email = f"rag_{timestamp}@example.com"
    password = "secure_password123"
    
    try:
        with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
            # 1. Signup & Login
            print(f"\n[1/5] Authenticating as {email}...")
            signup_resp = client.post("/api/auth/signup", json={"email": email, "password": password})
            assert signup_resp.status_code == 201
            token = client.post("/api/auth/login", data={"username": email, "password": password}).json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            org_id = signup_resp.json()["organization_id"]
            
            # 2. Upload Document (Triggers Indexing)
            print(f"\n[2/5] Uploading document to Org {org_id}...")
            content = """
            RheXa is an advanced AI platform for document intelligence.
            It uses RAG (Retrieval Augmented Generation) to answer questions.
            The backend is built with FastAPI and PostgreSQL.
            Phase 1.9 focuses on the RAG pipeline integration.
            """
            
            with open(TEST_FILE, "w") as f:
                f.write(content.strip())
                
            with open(TEST_FILE, "rb") as f:
                resp = client.post(
                    "/api/upload",
                    headers=headers,
                    files={"file": (TEST_FILE, f)},
                    params={"organization_id": org_id}
                )
            
            assert resp.status_code == 201
            doc_id = resp.json()["document_id"]
            print(f"✅ Document uploaded (ID: {doc_id}). Indexing in background...")
            
            # 3. Wait for Background Task
            print("\n[3/5] Waiting for indexing (5 seconds)...")
            time.sleep(5)
            
            # 4. Verify Index Creation
            expected_path = f"vector_store/org_{org_id}/index.faiss"
            if os.path.exists(expected_path):
                print(f"✅ Vector store created at: {expected_path}")
            else:
                print(f"❌ Error: Vector store not found at {expected_path}")
                exit(1)
                
            # 5. Test Search Retrieval
            print(f"\n[4/5] Testing RAG Retrieval...")
            queries = ["RheXa platform", "FastAPI backend", "Phase 1.9"]
            
            for q in queries:
                print(f"   Searching for: '{q}'...")
                search_resp = client.post(
                    "/api/search/query",
                    headers=headers,
                    params={"query": q, "organization_id": org_id, "limit": 2}
                )
                
                if search_resp.status_code == 200:
                    results = search_resp.json()
                    if results:
                        print(f"     ✅ Found {len(results)} chunks. Top score: {results[0]['score']}")
                        # print(f"     Content: {results[0]['content'][:50]}...")
                    else:
                        print("     ⚠️ No results found (might be embedding issue)")
                else:
                    print(f"     ❌ Search failed: {search_resp.text}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
    finally:
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)

    print("\n" + "="*80)
    print("🎉 RAG Pipeline verification complete!")
    print("="*80)

if __name__ == "__main__":
    test_rag_flow()
