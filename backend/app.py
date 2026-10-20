######STRIPPED CODE OF MYSQL FOR DEPLOYMENT TESTING NO RDS SETUP

    
  
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

