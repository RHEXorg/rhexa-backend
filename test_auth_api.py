# test_auth_api.py
"""
Integration test for RheXa Auth & Protected Upload.
"""

import httpx
import time
import os

BASE_URL = "http://127.0.0.1:8000"

def test_auth_flow():
    print("="*80)
    print("RheXa Auth & Security - Integration Test")
    print("="*80)
    
    timestamp = int(time.time())
    email = f"test_{timestamp}@example.com"
    password = "secure_password123"
    
    try:
        with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
            # 1. Signup
            print(f"\n[1/5] Signing up user {email}...")
            signup_resp = client.post(
                "/api/auth/signup",
                json={"email": email, "password": password}
            )
            assert signup_resp.status_code == 201
            user_data = signup_resp.json()
            org_id = user_data["organization_id"]
            print(f"✅ Signup successful! User ID: {user_data['id']}, Org ID: {org_id}")
            
            # 2. Login
            print(f"\n[2/5] Logging in to get JWT token...")
            login_resp = client.post(
                "/api/auth/login",
                data={"username": email, "password": password}
            )
            assert login_resp.status_code == 200
            token = login_resp.json()["access_token"]
            print("✅ Login successful! JWT token received.")
            
            headers = {"Authorization": f"Bearer {token}"}
            
            # 3. Check /me
            print(f"\n[3/5] Verifying JWT with /auth/me...")
            me_resp = client.get("/api/auth/me", headers=headers)
            assert me_resp.status_code == 200
            assert me_resp.json()["email"] == email
            print(f"✅ Identity verified for {email}")
            
            # 4. Try Upload with Token
            print(f"\n[4/5] Testing protected upload with JWT...")
            test_file = "auth_test.txt"
            with open(test_file, "w") as f:
                f.write("Secured content for authorized users only.")
                
            with open(test_file, "rb") as f:
                upload_resp = client.post(
                    "/api/upload",
                    headers=headers,
                    files={"file": (test_file, f)},
                    params={"organization_id": org_id}
                )
            
            os.remove(test_file)
            
            if upload_resp.status_code == 201:
                print("✅ Protected upload successful!")
            else:
                print(f"❌ Upload failed: {upload_resp.text}")
                
            # 5. Multi-tenant Check (Try to access another org)
            print(f"\n[5/5] Multi-tenant check: Trying to upload to Org 999...")
            with open("dummy.txt", "w") as f: f.write("dummy")
            with open("dummy.txt", "rb") as f:
                bad_resp = client.post(
                    "/api/upload",
                    headers=headers,
                    files={"file": ("dummy.txt", f)},
                    params={"organization_id": 999}
                )
            os.remove("dummy.txt")
            
            if bad_resp.status_code == 403:
                print("✅ Multi-tenant isolation verified! (Access Denied as expected)")
            else:
                print(f"❌ Security violation! Should be 403 but got {bad_resp.status_code}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
    print("\n" + "="*80)
    print("🎉 Auth Integration test complete!")
    print("="*80)

if __name__ == "__main__":
    test_auth_flow()
