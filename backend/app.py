from flask import Flask, send_from_directory, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
from pathlib import Path
from dotenv import load_dotenv

# TEMPORARY POC VERSION: no MySQL. All created users/stocks are lost on restart.
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or os.urandom(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
FRONTEND_DIR = Path(__file__).resolve().parent.parent / 'frontend'

# In-memory demo records. Single worker only, not suitable for production.
users = {}
next_user_id = 1
stocks = {
    'AAPL': {'ticker': 'AAPL', 'company_name': 'Apple Inc.', 'current_price': 250.00, 'opening_price': 248.50, 'day_high': 251.20, 'day_low': 247.80, 'available_shares': 1000},
    'MSFT': {'ticker': 'MSFT', 'company_name': 'Microsoft Corporation', 'current_price': 520.00, 'opening_price': 517.00, 'day_high': 522.00, 'day_low': 515.50, 'available_shares': 1000},
    'NVDA': {'ticker': 'NVDA', 'company_name': 'NVIDIA Corporation', 'current_price': 180.00, 'opening_price': 178.00, 'day_high': 182.50, 'day_low': 177.10, 'available_shares': 1000},
}

# Landing page
@app.route('/')
def home():
    return '''
    <h1>Stockboy backend is running! (POC mode)</h1>
    <a href="/frontend/"><button>Open Stockboy</button></a>
    '''

@app.route('/frontend/')
def frontend_home():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/frontend/<path:filename>')
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route('/api/status')
def status():
    return {'status': 'success', 'message': 'Stockboy API is running', 'mode': 'demo'}

@app.route('/api/db-test')
def db_test():
    return {'status': 'success', 'database': None, 'message': 'POC mode: MySQL is disabled', 'mode': 'demo'}

@app.route('/api/users', methods=['POST'])
def register():
    global next_user_id
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    if not all([full_name, username, email, password]):
        return 'All fields are required.', 400
    if any(u['username'].lower() == username.lower() or u['email'].lower() == email.lower() for u in users.values()):
        return 'Username or email already exists.', 409
    user_id = next_user_id
    next_user_id += 1
    users[user_id] = {
        'user_id': user_id,
        'full_name': full_name,
        'username': username,
        'email': email,
        'password_hash': generate_password_hash(password, method='pbkdf2:sha256'),
        'role': 'user',
    }
    return redirect('/frontend/login.html')

@app.route('/api/login', methods=['POST'])
def login():
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    user = next((u for u in users.values() if u['username'] == username), None)
    if user is None or not check_password_hash(user['password_hash'], password):
        return 'Invalid username or password.', 401
    session.clear()
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['role'] = user['role']
    return redirect('/frontend/account.html')

@app.route('/api/me')
def current_user():
    user = users.get(session.get('user_id'))
    if user is None:
        return {'error': 'Not logged in'}, 401
    return {key: user[key] for key in ['user_id', 'full_name', 'username', 'email', 'role']}

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect('/frontend/index.html')

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    return {'status': 'success', 'stocks': sorted(stocks.values(), key=lambda stock: stock['ticker']), 'mode': 'demo'}

@app.route('/api/stocks/<ticker>', methods=['GET'])
def get_stock(ticker):
    stock = stocks.get(ticker.upper())
    if stock is None:
        return {'status': 'error', 'message': 'Stock not found'}, 404
    return {'status': 'success', 'stock': stock, 'mode': 'demo'}

@app.route('/api/admin/stocks', methods=['POST'])
def create_stock():
    if 'user_id' not in session:
        return 'You must be logged in.', 401
    if session.get('role') != 'admin':
        return 'Admin access required.', 403

    ticker = request.form.get('ticker', '').strip().upper()
    company_name = request.form.get('company_name', '').strip()
    volume = request.form.get('volume', '').strip()
    initial_price = request.form.get('initial_price', '').strip()
    if not all([ticker, company_name, volume, initial_price]):
        return 'All fields are required.', 400
    if ticker in stocks:
        return 'That ticker already exists.', 409
    try:
        available_shares = int(volume)
        price = float(initial_price)
        if available_shares < 0 or not (0 < price < float('inf')):
            raise ValueError
    except ValueError:
        return 'Volume must be nonnegative and price must be a positive number.', 400
    stocks[ticker] = {
        'ticker': ticker, 'company_name': company_name,
        'available_shares': available_shares,
        'current_price': price, 'opening_price': price,
        'day_high': price, 'day_low': price,
    }
    return redirect('/frontend/stocks.html')

if __name__ == '__main__':
    app.run(debug=False)

