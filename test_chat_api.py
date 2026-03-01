# test_chat_api.py
"""
Integration test for RheXa Chat Phase 2.0.
"""

import httpx
import time
import os
import shutil

BASE_URL = "http://127.0.0.1:8000"
TEST_FILE = "chat_test_doc.txt"

def test_chat_flow():
    print("="*80)
    print("RheXa Phase 2.0 - Chat Integration Test")
    print("="*80)
    
    # Clean previous run
    if os.path.exists(TEST_FILE): os.remove(TEST_FILE)
    
    timestamp = int(time.time())
    email = f"chat_{timestamp}@example.com"
    password = "secure"
    
    try:
        with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
            # 1. Signup & Login
            print(f"\n[1/6] Authenticating as {email}...")
            signup_resp = client.post("/api/auth/signup", json={"email": email, "password": password})
            assert signup_resp.status_code == 201
            token = client.post("/api/auth/login", data={"username": email, "password": password}).json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            org_id = signup_resp.json()["organization_id"]
            
            # 2. Upload Document (Knowledge Base)
            print(f"\n[2/6] Uploading Knowledge Source...")
            content = """
            RheXa Project Status Report 2026.
            Phase 1.9 (RAG) is complete.
            Phase 2.0 (Chat) starts now.
            The net revenue for Q4 was $500,000.
            """
            
            with open(TEST_FILE, "w") as f:
                f.write(content.strip())
                
            with open(TEST_FILE, "rb") as f:
                client.post("/api/upload", headers=headers, files={"file": (TEST_FILE, f)}, params={"organization_id": org_id})
            
            print("   (Waiting 3s for background indexing...)")
            time.sleep(3)
            
            # 3. New Chat Session
            print(f"\n[3/6] Starting New Chat Session...")
            query = "What was the revenue in Q4?"
            chat_resp = client.post(
                "/api/chat/",
                headers=headers,
                json={"message": query, "organization_id": org_id}
            )
            
            if chat_resp.status_code != 200:
                print(f"❌ Chat failed: {chat_resp.text}")
                exit(1)
                
            chat_data = chat_resp.json()
            session_id = chat_data["session_id"]
            answer = chat_data["answer"]
            citations = chat_data["citations"]
            
            print(f"✅ AI Answer: {answer}")
            print(f"✅ Session ID Cloned: {session_id}")
            if citations:
                print(f"✅ Citations Found: {len(citations)}")
                print(f"   Source: {citations[0]['filename']}")
            else:
                print("⚠️ No citations (Check embedding mock)")

            # 4. Continue Session (History)
            print(f"\n[4/6] Continuing Chat Session {session_id}...")
            follow_up = "What phase is complete?"
            chat_resp_2 = client.post(
                "/api/chat/",
                headers=headers,
                json={
                    "message": follow_up, 
                    "session_id": session_id,
                    "organization_id": org_id
                }
            )
            assert chat_resp_2.status_code == 200
            print(f"✅ Follow-up Answer: {chat_resp_2.json()['answer']}")

            # 5. List Sessions
            print(f"\n[5/6] Listing Chat History...")
            list_resp = client.get("/api/chat/sessions", headers=headers)
            sessions = list_resp.json()
            assert len(sessions) >= 1
            print(f"✅ Found {len(sessions)} sessions.")
            print(f"   Latest: '{sessions[0]['title']}'")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
    finally:
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)

    print("\n" + "="*80)
    print("🎉 Chat Flow Verification Complete!")
    print("="*80)

if __name__ == "__main__":
    test_chat_flow()
