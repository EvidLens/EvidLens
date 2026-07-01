from flask import Flask, request, jsonify, render_template_string, redirect, session
import os 
import requests 
import base64
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "lensconnectdevkey123")

# ===== M-PESA SANDBOX CONFIG =====
CONSUMER_KEY = 'LeGawPo7b4x93kIGli7D8AIAr5LAWT9cHDtF58YyxqFtZ09f'
CONSUMER_SECRET = 'u5jkHpE4epBHu6nRZFzX0b3keVGTCqR9upjybehiX0md8GOYkLanq1R0Vh2OOHAT'
BUSINESS_SHORT_CODE = '174379' 
PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
CALLBACK_URL = 'https://lensconnect-x1uh.onrender.com/mpesa/confirmation'

def get_access_token():
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(api_url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    try: return r.json()['access_token']
    except: return None

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'lensconnect.db')
os.makedirs(os.path.dirname(db_path), exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    balance = db.Column(db.Float, default=0.0)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    amount = db.Column(db.Float)
    bundle_name = db.Column(db.String(50))
    mpesa_code = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20), default="PAID")

with app.app_context(): db.create_all()

# ===== ALL BUNDLES FROM YOUR SCREENSHOT =====
PRICES = {
    19: "1GB_1HR", 20: "250MB_24HRS", 49: "350MB_7DAYS", 50: "1.5GB_3HRS", 
    55: "1.25GB_TILL_MIDNIGHT", 99: "1GB_24HRS", 300: "2.5GB_7DAYS", 700: "6GB_7DAYS",
    23: "1GB_1HR_TUNUKIWA", 51: "1.5GB_3HRS_TUNUKIWA", 110: "2GB_24HRS_TUNUKIWA",
    22: "43MINS_3HRS", 52: "50MINS_TILL_MID", 5: "20SMS_24HRS", 
    10: "200SMS_24HRS", 30: "1000SMS_7DAYS", 101: "1500SMS_30DAYS",
}

def process_bundle(phone, amount, mpesa_code):
    bundle = PRICES.get(amount, "UNKNOWN_BUNDLE")
    print(f"SIMULATED: Sending {bundle} to {phone}. Code: {mpesa_code}")
    txn = Transaction.query.filter_by(mpesa_code=mpesa_code).first()
    if txn:
        txn.status = "FULFILLED"
        db.session.commit()

# ===== M-PESA STYLE LAYOUT =====
BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>LensConnect</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style> body { font-family: 'Inter', sans-serif; background-color: #F3F4F6; }.bg-mpesa { background: linear-gradient(135deg, #00A651 0%, #006D3A 100%); } </style>
</head>
<body class="pb-24">
    <div class="max-w-md mx-auto bg-gray-100 min-h-screen relative">
        {{ content|safe }}
    </div>
    {% if show_nav %}
    <nav class="fixed bottom-0 w-full max-w-md mx-auto bg-white border-t border-gray-200 flex justify-around py-2 shadow-[0_-2px_10px_rgba(0,0,0,0.05)]">
        <a href="/dashboard" class="flex flex-col items-center text-green-600"><i data-lucide="home" class="w-6 h-6"></i><span class="text-xs">Home</span></a>
        <a href="/bundles" class="flex flex-col items-center text-gray-400"><i data-lucide="package" class="w-6 h-6"></i><span class="text-xs">Bundles</span></a>
        <a href="#" class="flex flex-col items-center text-gray-400"><i data-lucide="file-text" class="w-6 h-6"></i><span class="text-xs">Bills</span></a>
        <a href="#" class="flex flex-col items-center text-gray-400"><i data-lucide="user" class="w-6 h-6"></i><span class="text-xs">Account</span></a>
    </nav>
    <script>lucide.createIcons();</script>
    {% endif %}
</body>
</html>
"""

# ===== PAGE CONTENT BLOCKS =====
AUTH_CONTENT = """<div class="p-8 pt-16"><h1 class="text-3xl font-bold text-gray-800">LensConnect</h1><p class="text-gray-500 mb-8">Buy Data, SMS, Minutes</p>{{ form_content|safe }}</div>"""
SIGNUP_FORM = """<form method="post" class="space-y-4"><input name="email" type="email" placeholder="Email" required class="w-full px-4 py-3 bg-white border rounded-xl"><input name="password" type="password" placeholder="Password" required class="w-full px-4 py-3 bg-white border rounded-xl"><button class="w-full py-3 font-bold text-white bg-green-600 rounded-xl">Signup</button></form><p class="text-sm text-center mt-4">Have an account? <a href="/login" class="text-green-600 font-semibold">Login</a></p>"""
LOGIN_FORM = """<form method="post" class="space-y-4"><input name="email" type="email" placeholder="Email" required class="w-full px-4 py-3 bg-white border rounded-xl"><input name="password" type="password" placeholder="Password" required class="w-full px-4 py-3 bg-white border rounded-xl"><button class="w-full py-3 font-bold text-white bg-green-600 rounded-xl">Login</button></form><p class="text-sm text-center mt-4">No account? <a href="/signup" class="text-green-600 font-semibold">Signup</a></p>"""

DASHBOARD_CONTENT = """
<div class="p-4">
    <div class="flex justify-between items-center mb-4">
        <p class="text-lg font-semibold">Hello {email} 👋</p>
        <a href="/logout"><i data-lucide="log-out" class="w-6 h-6 text-gray-600"></i></a>
    </div>
    <div class="bg-mpesa text-white p-5 rounded-2xl shadow-lg">
        <p class="text-sm opacity-80">Wallet Balance</p>
        <p class="text-4xl font-bold my-2">Ksh {balance}</p>
        <div class="flex gap-3 mt-4">
            <button class="flex-1 bg-white/20 py-2 rounded-lg text-sm">Statement</button>
            <a href="/bundles" class="flex-1 bg-white/20 py-2 rounded-lg text-sm text-center">Top Up</a>
        </div>
    </div>
    <div class="bg-white p-4 rounded-2xl mt-6">
        <div class="flex justify-between items-center mb-3"><p class="font-semibold">Quick Actions</p><a href="/bundles" class="text-sm text-green-600">Manage</a></div>
        <div class="grid grid-cols-4 gap-4 text-center">
            <a href="/bundles?tab=data" class="flex flex-col items-center gap-1"><div class="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center"><i data-lucide="smartphone" class="w-7 h-7 text-green-600"></i></div><span class="text-xs text-gray-600">Data</span></a>
            <a href="/bundles?tab=minutes" class="flex flex-col items-center gap-1"><div class="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center"><i data-lucide="phone" class="w-7 h-7 text-blue-600"></i></div><span class="text-xs text-gray-600">Minutes</span></a>
            <a href="/bundles?tab=sms" class="flex flex-col items-center gap-1"><div class="w-14 h-14 bg-purple-100 rounded-full flex items-center justify-center"><i data-lucide="message-square" class="w-7 h-7 text-purple-600"></i></div><span class="text-xs text-gray-600">SMS</span></a>
            <a href="/bundles?tab=tunukiwa" class="flex flex-col items-center gap-1"><div class="w-14 h-14 bg-yellow-100 rounded-full flex items-center justify-center"><i data-lucide="zap" class="w-7 h-7 text-yellow-600"></i></div><span class="text-xs text-gray-600">Tunukiwa</span></a>
        </div>
    </div>
</div>
"""

BUNDLES_PAGE = """
<div class="p-4">
    <a href="/dashboard" class="flex items-center gap-2 mb-4 text-gray-600"><i data-lucide="arrow-left"></i> Back</a>
    <div class="flex border-b mb-4">
        <a href="/bundles?tab=data" class="flex-1 py-2 text-center font-semibold {% if tab=='data' %}border-b-2 border-green-600 text-green-600{% else %}text-gray-500{% endif %}">Data</a>
        <a href="/bundles?tab=minutes" class="flex-1 py-2 text-center font-semibold {% if tab=='minutes' %}border-b-2 border-green-600 text-green-600{% else %}text-gray-500{% endif %}">Minutes</a>
        <a href="/bundles?tab=sms" class="flex-1 py-2 text-center font-semibold {% if tab=='sms' %}border-b-2 border-green-600 text-green-600{% else %}text-gray-500{% endif %}">SMS</a>
    </div>
    <div class="space-y-3">
        {% for amount, name in bundles %}
        <form action="/stkpush" method="post" class="bg-white p-4 rounded-xl flex justify-between items-center shadow-sm">
            <input type="hidden" name="amount" value="{{ amount }}">
            <div>
                <p class="font-bold">{{ name.replace('_', ' ') }}</p>
                <p class="text-sm text-gray-500">Valid: {{ name.split('_')[-1] }}</p>
            </div>
            <button class="bg-green-600 text-white font-bold px-5 py-2 rounded-lg">Ksh {{ amount }}</button>
        </form>
        {% endfor %}
    </div>
</div>
"""

# ===== ROUTES =====
@app.route('/')
def home(): return redirect('/signup')
    
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        if User.query.filter_by(email=email).first(): return render_template_string(BASE_LAYOUT, content=AUTH_CONTENT.format(form_content="Email exists. <a href='/login'>Login</a>"), show_nav=False)
        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user); db.session.commit()
        session['user_id'] = user.id
        return redirect('/dashboard')
    return render_template_string(BASE_LAYOUT, content=AUTH_CONTENT.format(form_content=SIGNUP_FORM), show_nav=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['email'], request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect('/dashboard')
        return render_template_string(BASE_LAYOUT, content=AUTH_CONTENT.format(form_content="Invalid login. <a href='/login'>Try again</a>"), show_nav=False)
    return render_template_string(BASE_LAYOUT, content=AUTH_CONTENT.format(form_content=LOGIN_FORM), show_nav=False)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect('/login')
    user = User.query.get(session['user_id'])
    return render_template_string(BASE_LAYOUT, content=DASHBOARD_CONTENT.format(email=user.email.split('@')[0], balance=f"{user.balance:.2f}"), show_nav=True)

@app.route('/bundles')
def bundles():
    if 'user_id' not in session: return redirect('/login')
    tab = request.args.get('tab', 'data')
    if tab == 'data': items = {k: v for k, v in PRICES.items() if 'MB' in v or 'GB' in v and 'SMS' not in v and 'MINS' not in v}
    elif tab == 'minutes': items = {k: v for k, v in PRICES.items() if 'MINS' in v}
    elif tab == 'sms': items = {k: v for k, v in PRICES.items() if 'SMS' in v}
    else: items = {k: v for k, v in PRICES.items() if 'TUNUKIWA' in v}
    sorted_items = sorted(items.items())
    return render_template_string(BASE_LAYOUT, content=render_template_string(BUNDLES_PAGE, bundles=sorted_items, tab=tab), show_nav=True)

@app.route('/stkpush', methods=['POST'])
def stkpush():
    if 'user_id' not in session: return redirect('/login')
    phone = request.form['phone'] if 'phone' in request.form else '254700000' # For testing
    amount = int(request.form['amount'])
    access_token = get_access_token()
    if not access_token: return "Error getting token"
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode((BUSINESS_SHORT_CODE + PASSKEY + timestamp).encode()).decode('utf-8')
    payload = {"BusinessShortCode": BUSINESS_SHORT_CODE, "Password": password, "Timestamp": timestamp, "TransactionType": "CustomerPayBillOnline", "Amount": amount, "PartyA": phone, "PartyB": BUSINESS_SHORT_CODE, "PhoneNumber": phone, "CallBackURL": CALLBACK_URL, "AccountReference": "LensConnect", "TransactionDesc": PRICES.get(amount)}
    requests.post(api_url, json=payload, headers={"Authorization": f"Bearer {access_token}"})
    return render_template_string(BASE_LAYOUT, content=f"<div class='p-8 text-center'><i data-lucide='check-circle' class='w-16 h-16 text-green-500 mx-auto'></i><p class='mt-4 font-semibold'>STK sent for {PRICES.get(amount)}</p><a href='/bundles' class='text-green-600 mt-2 block'>Back to Bundles</a></div>", show_nav=True)

@app.route('/mpesa/confirmation', methods=['POST'])
def mpesa_confirmation():
    data = request.get_json()
    if data['Body']['stkCallback']['ResultCode'] == 0:
        callback = data['Body']['stkCallback']['CallbackMetadata']['Item']
        amount = int(next(item['Value'] for item in callback if item['Name'] == 'Amount'))
        mpesa_code = next(item['Value'] for item in callback if item['Name'] == 'MpesaReceiptNumber')
        phone = str(next(item['Value'] for item in callback if item['Name'] == 'PhoneNumber'))
        bundle_name = PRICES.get(amount, "UNKNOWN")
        if not Transaction.query.filter_by(mpesa_code=mpesa_code).first():
            txn = Transaction(phone=phone, amount=amount, bundle_name=bundle_name, mpesa_code=mpesa_code)
            db.session.add(txn)
            user = User.query.get(session.get('user_id')) 
            if user: user.balance += amount
            db.session.commit()
            process_bundle(phone, amount, mpesa_code)
        return jsonify({"ResultCode": 0, "ResultDesc": "Accepted"})
    return jsonify({"ResultCode": 1, "ResultDesc": "Failed"})

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
