# test_upload_api.py
"""
Professional test script for RheXa Upload API.

This script tests:
1. Uploading a TXT file
2. Listing all documents
3. Getting document details
4. Deleting a document

Requirements:
pip install httpx
"""

import os
import httpx
import time

BASE_URL = "http://127.0.0.1:8000"

def test_upload_flow():
    print("="*80)
    print("RheXa Upload API - Integration Test")
    print("="*80)
    
    # 1. Create a dummy file
    test_filename = "api_test_doc.txt"
    test_content = "This is a test document for the RheXa Upload API flow."
    with open(test_filename, "w") as f:
        f.write(test_content)
    
    try:
        with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
            # Step 1: Upload
            print(f"\n[1/4] Uploading {test_filename}...")
            with open(test_filename, "rb") as f:
                response = client.post(
                    "/api/upload",
                    files={"file": (test_filename, f, "text/plain")},
                    params={"organization_id": 1}
                )
            
            if response.status_code != 201:
                print(f"❌ Upload failed: {response.text}")
                return
            
            data = response.json()
            doc_id = data["document_id"]
            print(f"✅ Uploaded successfully! Document ID: {doc_id}")
            print(f"📊 Extracted text length: {data['extracted_text_length']}")
            print(f"⏱️  Processing time: {data['processing_time_ms']}ms")
            
            # Step 2: List documents
            print(f"\n[2/4] Listing documents for org 1...")
            response = client.get("/api/documents", params={"organization_id": 1})
            if response.status_code == 200:
                docs_list = response.json()
                print(f"✅ Found {docs_list['total']} documents.")
            else:
                print(f"❌ List failed: {response.text}")
            
            # Step 3: Get document details
            print(f"\n[3/4] Fetching details for Document {doc_id}...")
            response = client.get(f"/api/documents/{doc_id}", params={"organization_id": 1})
            if response.status_code == 200:
                doc_details = response.json()
                print(f"✅ Filename: {doc_details['filename']}")
                print(f"✅ Type: {doc_details['file_type']}")
            else:
                print(f"❌ Detail fetch failed: {response.text}")
                
            # Step 4: Delete document
            print(f"\n[4/4] Deleting Document {doc_id}...")
            response = client.delete(f"/api/documents/{doc_id}", params={"organization_id": 1})
            if response.status_code == 204:
                print(f"✅ Document deleted successfully.")
            else:
                print(f"❌ Delete failed: {response.text}")
                
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(test_filename):
            os.remove(test_filename)
            
    print("\n" + "="*80)
    print("🎉 Integration test complete!")
    print("="*80)

if __name__ == "__main__":
    test_upload_flow()
