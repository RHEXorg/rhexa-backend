from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import require_organization_access
from app.services.billing_service import get_org_usage
from app.models.organization import Organization
from datetime import datetime, timezone, timedelta
import requests
import hmac
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

# Lemon Squeezy Config
LS_API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5NGQ1OWNlZi1kYmI4LTRlYTUtYjE3OC1kMjU0MGZjZDY5MTkiLCJqdGkiOiI0M2Q4Y2Y0MDkwYzQ0NjA1YThiYzgzZDY0NGM2YmRiNDRkMmNlY2I5ZTViZGM2NDA2MjNkOWE0NTZhNzAzMTFlMDk3N2RmMmFiYTc2OTYyZCIsImlhdCI6MTc3MjM1ODIxMC42NDMzNTIsIm5iZiI6MTc3MjM1ODIxMC42NDMzNTUsImV4cCI6MTc4ODIyMDgwMC4wMTk4NzEsInN1YiI6IjY0MDU4NDMiLCJzY29wZXMiOltdfQ.m2rOZlHEh7GUZ0rrB0dO1L06eEGF19lubUWNzPFL3q-B1Y7Fi3eMQ-OcYmExbHU52qR5ChCBHeZ11aOB8ZSBq5Cint2OZQwg6Phim4fs4icKsR4EAPU8F9pJtcuUEdVmOOvt5WEXgBBjYL4vUjpV48iuHoVDsm5SfaFL4XfLFjjTxuugcxunsl1doDlo0tkyb3mQ0a5DjWkT3B8B5UC1ZbDbbBTeHPgrtCXxHKDbwwYJ7HAMn1Ply7mDL1Ry-g4WMN0KJVit4EAzNWQElDGmm0sewHuimgAvRZ1ELFFH7-ouIpEspzpajcDSf0jO3pe_SGz5rfB4CfipKwCOVlgpmOe5Xb9rAlTpSLEAANvkz9gss_n-j7Ryiny3xp0pBXLUZsIu-8pfxvt60ytzFUOaBAFbkgmdWFxx2yB2oYczVLKMMQLJCNdggWhsVTxlDV5A9P4ejPa4IXeN899z4-xzejHhQxIUweMPNHT4kZ-Fyn4psVjZHJdT2CXCUvBS0zOhl7liJ_eNj4XoaxEs8fABlVskhTVenSLIfPOheg0iprwPOToX2y_6UXs0ZHn5YlREUbASXqCbgYlza8BVg-VhtR0jZZZF23tH8_tVieSRhkaA06obfpic_5dbWY5G6BDK21W_NHTXQ5YiaXjq8DHWnV0rdKUe9fWQP0MeBR-GXxs"
LS_STORE_ID = "279707"
LS_WEBHOOK_SECRET = "rhexa_lemon_secret_2026"
VARIANT_PRO = "1355396" # 6 dollar plan
VARIANT_ENTERPRISE = "1355394" # 13 dollar plan

router = APIRouter(prefix="/api/billing", tags=["billing"])

@router.get("/")
def get_billing_status(
    current_org_id: int = Depends(require_organization_access),
    db: Session = Depends(get_db)
):
    # Auto-initialize trial if none exists
    org = db.query(Organization).filter(Organization.id == current_org_id).first()
    if org and org.subscription_tier == "free_trial" and not org.trial_ends_at:
        org.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=2)
        db.commit()
        
    return get_org_usage(db, current_org_id)

@router.post("/upgrade")
def create_checkout(
    plan: str,
    current_org_id: int = Depends(require_organization_access),
    db: Session = Depends(get_db)
):
    if plan not in ["pro", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid plan")
        
    org = db.query(Organization).filter(Organization.id == current_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
        
    variant_id = VARIANT_PRO if plan == "pro" else VARIANT_ENTERPRISE
    
    # Create Local Checkout URL via Lemon Squeezy API
    headers = {
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
        "Authorization": f"Bearer {LS_API_KEY}"
    }
    
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "custom": {
                        "org_id": str(current_org_id)
                    }
                }
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": LS_STORE_ID
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": variant_id
                    }
                }
            }
        }
    }

    resp = requests.post("https://api.lemonsqueezy.com/v1/checkouts", headers=headers, json=payload)
    if resp.status_code >= 400:
        logger.error(f"Failed to create checkout: {resp.text}")
        raise HTTPException(status_code=500, detail="Could not generate payment link.")
        
    checkout_url = resp.json()['data']['attributes']['url']
    return {"checkout_url": checkout_url}


@router.post("/webhook")
async def lemon_squeezy_webhook(request: Request, db: Session = Depends(get_db)):
    # 1. Verify payload signature
    signature = request.headers.get("x-signature")
    body = await request.body()
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
        
    digest = hmac.new(
        LS_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(digest, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    # 2. Process webhook
    try:
        data = await request.json()
        event_name = data.get("meta", {}).get("event_name")
        custom_data = data.get("meta", {}).get("custom_data", {})
        org_id = custom_data.get("org_id")
        
        if not org_id:
            return {"status": "ignored", "reason": "No org_id in custom_data"}
            
        org = db.query(Organization).filter(Organization.id == int(org_id)).first()
        if not org:
            return {"status": "error", "reason": "Org not found"}

        attributes = data.get("data", {}).get("attributes", {})
        variant_id = str(attributes.get("variant_id"))
        status = attributes.get("status")

        if event_name in ["subscription_created", "subscription_updated"]:
            if status in ["active", "past_due"]:
                if variant_id in [VARIANT_PRO, "1355376"]: # accounting for both 6 dollar variants
                    org.subscription_tier = "pro"
                elif variant_id == VARIANT_ENTERPRISE:
                    org.subscription_tier = "enterprise"
                
                org.billing_cycle = "2_months"
                org.trial_ends_at = None
                
            elif status in ["unpaid", "cancelled", "expired"]:
                org.subscription_tier = "free_trial"
                org.trial_ends_at = datetime.now(timezone.utc) # expire immediately
                
            db.commit()
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return {"status": "error"}
