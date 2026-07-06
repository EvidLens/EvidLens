import os
import base64
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from.models import Payment, Subscription, MpesaTransaction, PaymentStatus, SubscriptionTier

MPESA_CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
MPESA_CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
MPESA_BUSINESS_SHORTCODE = os.getenv("MPESA_BUSINESS_SHORTCODE", "174379")
MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
MPESA_CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL")

DARAJA_BASE = "https://sandbox.safaricom.co.ke" # Change to https://api.safaricom.co.ke for prod

def get_access_token():
    """Get OAuth token from Daraja"""
    url = f"{DARAJA_BASE}/oauth/v1/generate?grant_type=client_credentials"
    response = requests.get(url, auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET))
    return response.json()["access_token"]

def generate_password():
    """Generate STK password"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    data = MPESA_BUSINESS_SHORTCODE + MPESA_PASSKEY + timestamp
    password = base64.b64encode(data.encode()).decode()
    return password, timestamp

def initiate_stk_push(db: Session, phone: str, amount: float, payment_type: str, description: str, reference_id: int = None):
    """Send STK Push to user. Powers SME Pro, Business, Pay-Per-Report"""
    phone = phone.replace("+254", "254").replace("0", "254", 1)
    token = get_access_token()
    password, timestamp = generate_password()
    
    payment = Payment(
        user_id=1, # Replace with auth user_id
        phone_number=phone,
        amount_kes=amount,
        payment_type=payment_type,
        reference_id=reference_id,
        description=description,
        status=PaymentStatus.PENDING
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    payload = {
        "BusinessShortCode": MPESA_BUSINESS_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": MPESA_BUSINESS_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": MPESA_CALLBACK_URL,
        "AccountReference": f"EvidLens{payment.id}",
        "TransactionDesc": description
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{DARAJA_BASE}/mpesa/stkpush/v1/processrequest", json=payload, headers=headers)
    res = r.json()
    
    if "CheckoutRequestID" in res:
        payment.checkout_request_id = res["CheckoutRequestID"]
        db.commit()
    
    return {
        "success": "CheckoutRequestID" in res,
        "checkout_request_id": res.get("CheckoutRequestID"),
        "message": res.get("ResponseDescription", "Failed")
    }

def handle_c2b_webhook(db: Session, payload: dict):
    """Process Safaricom callback. Updates payment + subscription"""
    body = payload.get("Body", {}).get("stkCallback", {})
    checkout_id = body.get("CheckoutRequestID")
    result_code = body.get("ResultCode")
    
    payment = db.query(Payment).filter(Payment.checkout_request_id==checkout_id).first()
    if not payment:
        return
    
    if result_code == 0:
        # Success
        items = body["CallbackMetadata"]["Item"]
        receipt = next((i["Value"] for i in items if i["Name"]=="MpesaReceiptNumber"), None)
        payment.status = PaymentStatus.SUCCESS
        payment.mpesa_receipt_number = receipt
        payment.completed_at = datetime.now()
        
        # Save raw transaction
        trans = MpesaTransaction(
            payment_id=payment.id,
            transaction_type="STKPush",
            trans_id=receipt,
            raw_callback=payload
        )
        db.add(trans)
        
        # Activate subscription or credits
        activate_purchase(db, payment)
    else:
        payment.status = PaymentStatus.FAILED
    
    db.commit()

def activate_purchase(db: Session, payment: Payment):
    """Grant access based on payment_type"""
    sub = get_subscription(db, payment.user_id)
    
    if payment.payment_type == "subscription":
        # Upgrade tier
        if payment.amount_kes >= 40000:
            tier = SubscriptionTier.ENTERPRISE
        elif payment.amount_kes >= 15000:
            tier = SubscriptionTier.BUSINESS
        elif payment.amount_kes >= 5000:
            tier = SubscriptionTier.PROFESSIONAL
        else:
            tier = SubscriptionTier.SME_PRO
        
        sub.tier = tier
        sub.status = "active"
        sub.current_period_end = datetime.now() + timedelta(days=30)
        sub.auto_renew = True
        set_tier_limits(sub)
    
    elif payment.payment_type == "report":
        sub.reports_left += 1
    
    db.commit()

def process_b2c(db: Session, user_id: int, phone: str, amount: float, reason: str):
    """Send money out. For refunds and referrals"""
    token = get_access_token()
    payload = {
        "InitiatorName": "evidlens",
        "SecurityCredential": os.getenv("MPESA_B2C_SECURITY"),
        "CommandID": "BusinessPayment",
        "Amount": int(amount),
        "PartyA": MPESA_BUSINESS_SHORTCODE,
        "PartyB": phone,
        "Remarks": reason,
        "QueueTimeOutURL": MPESA_CALLBACK_URL,
        "ResultURL": MPESA_CALLBACK_URL,
        "Occasion": "Referral"
    }
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{DARAJA_BASE}/mpesa/b2c/v1/paymentrequest", json=payload, headers=headers)
    return r.json()

def verify_payment_status(db: Session, checkout_request_id: str):
    return db.query(Payment).filter(Payment.checkout_request_id==checkout_request_id).first()

def get_subscription(db: Session, user_id: int):
    sub = db.query(Subscription).filter(Subscription.user_id==user_id).first()
    if not sub:
        sub = Subscription(user_id=user_id, tier=SubscriptionTier.FREE)
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub

def create_subscription(db: Session, user_id: int, tier: SubscriptionTier, auto_renew: bool):
    sub = get_subscription(db, user_id)
    sub.tier = tier
    sub.auto_renew = auto_renew
    set_tier_limits(sub)
    db.commit()
    return sub

def set_tier_limits(sub: Subscription):
    """Apply limits from Section 7 pricing"""
    limits = {
        SubscriptionTier.FREE: {"searches": 3, "ai": 10, "reports": 1, "api": 0},
        SubscriptionTier.SME_STARTER: {"searches": 10, "ai": 50, "reports": 1, "api": 0},
        SubscriptionTier.SME_PRO: {"searches": 9999, "ai": 9999, "reports": 9999, "api": 1000},
        SubscriptionTier.PROFESSIONAL: {"searches": 200, "ai": 500, "reports": 9999, "api": 10000},
        SubscriptionTier.BUSINESS: {"searches": 1000, "ai": 2000, "reports": 9999, "api": 100000},
        SubscriptionTier.ENTERPRISE: {"searches": 99999, "ai": 99999, "reports": 99999, "api": 999999},
    }
    l = limits[sub.tier]
    sub.searches_left = l["searches"]
    sub.ai_credits_left = l["ai"]
    sub.reports_left = l["reports"]
    sub.api_calls_left = l["api"]
