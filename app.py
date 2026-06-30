from flask import Flask, request, jsonify, render_template_string, redirect, session
import os 
import threading
import requests 
import base64
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lensconnectdevkey123") # Change this on Render later

# ===== M-PESA SANDBOX CONFIG =====
CONSUMER_KEY = 'LeGawPo7b4x93kIGli7D8AIAr5LAWT9cHDtF58YyxqFtZ09f'
CONSUMER_SECRET = 'u5jkHpE4epBHu6nRZFzX0b3keVGTCqR9upjybehiX0md8GOYkLanq1R0Vh2OOHAT'
BUSINESS_SHORT_CODE = '174379' 
PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
CALLBACK_URL = 'https://lensconnect-x1uh.onrender.com/mpesa/confirmation'
def get_access_token():
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(api_url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    return r.json()['access_token']

@app.route('/stkpush', methods=['POST'])
def stkpush():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    phone = request.form['phone'] # Must be 2547XX... format
    amount = 20
    
    access_token = get_access_token()
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((BUSINESS_SHORT_CODE + PASSKEY + timestamp).encode()).decode('utf-8')
    
    payload = {
        "BusinessShortCode": BUSINESS_SHORT_CODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": BUSINESS_SHORT_CODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": "LensConnect",
        "TransactionDesc": "Buy 250MB" 
    }
    headers = {"Authorization": "Bearer %s" % access_token}
    response = requests.post(api_url, json=payload, headers=headers)
    
    return f"STK Push sent to {phone}. Check your phone and enter M-PESA PIN. <a href='/dashboard'>Back</a>"

@app.route('/mpesa/confirmation', methods=['POST'])
def mpesa_confirmation():
    data = request.get_json()
    
    # Check if payment was successful. ResultCode 0 = Success
    if data['Body']['stkCallback']['ResultCode'] == 0:
        # For now we just print it. Next step: credit user balance here
        print("M-PESA Payment Successful:", data)
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})
    
    print("M-PESA Payment Failed:", data)
    return jsonify({"ResultCode": 1, "ResultDesc": "Failed"})

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'lensconnect.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

db = SQLAlchemy(app)

# ===== STEP 2: DATABASE USER MODEL =====
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    balance = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    amount = db.Column(db.Float)
    mpesa_code = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20))

with app.app_context():
    db.create_all()

PRICES = {
    19: "1GB_1HR", 20: "250MB_24HRS", 49: "350MB_7DAYS", 50: "1.5GB_3HRS", 
    55: "1.25GB_TILL_MIDNIGHT", 99: "1GB_24HRS", 300: "2.5GB_7DAYS", 700: "6GB_7DAYS",
    23: "1GB_1HR_TUNUKIWA", 51: "1.5GB_3HRS_TUNUKIWA", 110: "2GB_24HRS_TUNUKIWA",
    22: "43MINS_3HRS", 52: "50MINS_TILL_MID", 5: "20SMS_24HRS", 
    10: "200SMS_24HRS", 30: "1000SMS_7DAYS", 101: "1500SMS_30DAYS",
}

def process_bundle(phone, amount, mpesa_code):
    with app.app_context():
        bundle = PRICES.get(amount, "UNKNOWN")
        print(f"SIMULATED: Sending {bundle} to {phone}. Code: {mpesa_code}")
        txn = Transaction.query.filter_by(mpesa_code=mpesa_code).first()
        if txn:
            txn.status = "FULFILLED"
            db.session.commit()
        print(f"SIMULATED: Sending {bundle} to {phone}. Code: {mpesa_code}")
        txn = Transaction.query.filter_by(mpesa_code=mpesa_code).first()
        if txn:
            txn.status = "FULFILLED"
            db.session.commit()

# ===== STEP 1: SIGNUP/LOGIN ROUTES =====
SIGNUP_FORM = """
<h2>Signup</h2>
<form method="post">
  Email: <input name="email" type="email" required><br><br>
  Password: <input name="password" type="password" required><br><br>
  <button>Signup</button>
</form>
<p>Already have an account? <a href="/login">Login</a></p>
"""

LOGIN_FORM = """
<h2>Login</h2>
<form method="post">
  Email: <input name="email" type="email" required><br><br>
  Password: <input name="password" type="password" required><br><br>
  <button>Login</button>
</form>
<p>No account? <a href="/signup">Signup</a></p>
"""
@app.route('/')
def home():
    return redirect('/signup')
    
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            return "Email already exists. <a href='/login'>Login</a>"
        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        return redirect('/dashboard')
    return SIGNUP_FORM

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect('/dashboard')
        return "Invalid login. <a href='/login'>Try again</a>"
    return LOGIN_FORM

# ===== STEP 3: DASHBOARD PAGE =====
DASHBOARD_PAGE = """
<h2>Welcome, {email}</h2>
<p>Balance: Ksh {balance}</p>

<form action="/stkpush" method="post">
  <p>Buy 250MB 24HRS for Ksh 20</p>
  Enter M-PESA Phone: <input name="phone" type="text" placeholder="2547XXXXXXXX" required><br><br>
  <button>Buy Now - STK Push</button>
</form>
<br>
<a href='/logout'>Logout</a>
"""

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    return DASHBOARD_PAGE.format(email=user.email, balance=user.balance)

@app.route('/buy', methods=['POST'])
def buy():
    if 'user_id' not in session:
        return redirect('/login')
    user = User.query.get(session['user_id'])
    amount = float(request.form['amount'])
    
    if user.balance >= amount:
        user.balance -= amount
        db.session.commit()
        return f"Success! Sent 250MB 24HRS. New Balance: {user.balance} <a href='/dashboard'>Back</a>"
    else:
        return f"Balance too low: {user.balance}. <a href='/dashboard'>Back</a>"

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
