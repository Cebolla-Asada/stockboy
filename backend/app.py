from flask import Flask, send_from_directory, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
from pathlib import Path
from dotenv import load_dotenv


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
##connection with , sql server, db password should be
##your own personal password in .env from MySQL 
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

##basic landing page for flask server, takes u to index.html
@app.route("/")
def home():
    return """
    <h1>Stockboy backend is running!</h1>
    <a href="/frontend/">
        <button>Open Stockboy</button>
    </a>
    """

##routes to frontend DIR
@app.route("/frontend/")
def frontend_home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/frontend/<path:filename>")
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)

##api status check w/ postman
@app.route("/api/status")
def status():
    return {
        "status": "success",
        "message": "Stockboy API is running"
    }

##db status tester, creates a DB using the schema.db in DB folder
@app.route("/api/db-test")
def db_test():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT DATABASE()")
    database = cursor.fetchone()

    cursor.close()
    connection.close()

    return {
        "status": "success",
        "database": database[0]
    }
@app.route("/api/users", methods=["POST"])
def register():
    full_name = request.form.get("full_name")
    username = request.form.get("username")
    email = request.form.get("email")
    password = request.form.get("password")

    if not full_name or not username or not email or not password:
        return "All fields are required.", 400

    password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO users (full_name, username, email, password_hash)
            VALUES (%s, %s, %s, %s)
            """,
            (full_name, username, email, password_hash)
        )

        connection.commit()

    except mysql.connector.IntegrityError:
        cursor.close()
        connection.close()
        return "Username or email already exists.", 409

    cursor.close()
    connection.close()

    return redirect("/frontend/login.html")
    
    
    
##for loginpasswords
## login route
@app.route("/api/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE username = %s",
        (username,)
    )

    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if user is None:
        return "Invalid username or password.", 401

    if not check_password_hash(user["password_hash"], password):
        return "Invalid username or password.", 401

    session["user_id"] = user["user_id"]
    session["username"] = user["username"]
    session["role"] = user["role"]

    return redirect("/frontend/account.html")


@app.route("/api/me")
def current_user():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT user_id, full_name, username, email, role, cash_balance
        FROM users
        WHERE user_id = %s
        """,
        (session["user_id"],)
    )

    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if user is None:
        return {"error": "User not found"}, 404

    user["cash_balance"] = float(user["cash_balance"])

    return user

##route for logout button
@app.route("/api/logout")
def logout():
    session.clear()
    return redirect("/frontend/index.html")


    
@app.route("/api/stocks", methods=["GET"])
def get_stocks():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT stock_id, ticker, company_name, current_price,
                   opening_price, day_high, day_low, available_shares
            FROM stocks
            ORDER BY ticker
        """)

        stocks = cursor.fetchall()

        for stock in stocks:
            stock["current_price"] = float(stock["current_price"])
            stock["opening_price"] = float(stock["opening_price"])
            stock["day_high"] = float(stock["day_high"])
            stock["day_low"] = float(stock["day_low"])

        return {"status": "success", "stocks": stocks}

    except Exception:
        app.logger.exception("Failed to retrieve stocks")
        return {"status": "error", "message": "Unable to retrieve stocks"}, 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


@app.route("/api/stocks/<ticker>", methods=["GET"])
def get_stock(ticker):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT stock_id, ticker, company_name, current_price,
                   opening_price, day_high, day_low
            FROM stocks
            WHERE ticker = %s
        """, (ticker.upper(),))

        stock = cursor.fetchone()

        if stock is None:
            return {"status": "error", "message": "Stock not found"}, 404

        for field in ["current_price", "opening_price",
                      "day_high", "day_low"]:
            stock[field] = float(stock[field])

        return {"status": "success", "stock": stock}

    except Exception:
        app.logger.exception("Failed to retrieve stock")
        return {"status": "error", "message": "Unable to retrieve stock"}, 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


## Route to display User's Portfolio/Holdings
@app.route("/api/portfolio", methods=["GET"])
def get_portfolio():

    # Check whether the user is logged in
    if "user_id" not in session:
        return {"status": "error", "message": "Please log in first"}, 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        user_id = session["user_id"]

        cursor.execute("""
            SELECT
                h.holding_id,
                s.stock_id,
                s.ticker,
                s.company_name,
                h.share_num,
                s.current_price,
                (h.share_num * s.current_price) AS holding_value
            FROM holdings h
            JOIN stocks s ON h.stock_id = s.stock_id
            WHERE h.user_id = %s
            AND h.share_num > 0
            ORDER BY s.ticker
        """, (user_id,))

        holdings = cursor.fetchall()

        # Convert database decimal values to floats
        total_value = 0

        for holding in holdings:
            holding["current_price"] = float(holding["current_price"])
            holding["holding_value"] = float(holding["holding_value"])

            total_value += holding["holding_value"]

        return {
            "status": "success",
            "user_id": user_id,
            "holdings": holdings,
            "total_portfolio_value": round(total_value, 2)
        }

    except Exception:
        app.logger.exception("Failed to retrieve portfolio")
        return {
            "status": "error",
            "message": "Unable to retrieve portfolio"
        }, 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()


## Route to display User's Transaction History
@app.route("/api/transactions", methods=["GET"])
def get_transactions():

    # Check whether the user is logged in
    if "user_id" not in session:
        return {"status": "error", "message": "Please log in first"}, 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        user_id = session["user_id"]

        cursor.execute("""
            SELECT
                t.transaction_id,
                t.transaction_type,
                s.ticker,
                t.share_num,
                t.price,
                t.total_amount,
                t.transaction_date
            FROM transactions t
            JOIN stocks s ON t.stock_id = s.stock_id
            WHERE t.user_id = %s
            ORDER BY t.transaction_date DESC
        """, (user_id,))

        transactions = cursor.fetchall()

        # Convert database values into JSON-friendly values
        for transaction in transactions:
            transaction["price"] = float(transaction["price"])
            transaction["total_amount"] = float(transaction["total_amount"])

            if transaction["transaction_date"]:
                transaction["transaction_date"] = (
                    transaction["transaction_date"].strftime("%Y-%m-%d %H:%M:%S")
                )

        return {
            "status": "success",
            "transactions": transactions
        }

    except Exception:
        app.logger.exception("Failed to retrieve transaction history")

        return {
            "status": "error",
            "message": "Unable to retrieve transaction history"
        }, 500

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None and connection.is_connected():
            connection.close()

## Buy stock route
@app.route("/api/buy", methods=["POST"])
def buy_stock():

    if "user_id" not in session:
        return {"status": "error", "message": "Please log in first"}, 401

    data = request.get_json(silent=True) or {}

    try:
        stock_id = int(data.get("stock_id"))
        shares = int(data.get("shares"))
        if stock_id <= 0 or shares <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return {"status": "error", "message": "Invalid stock or share amount"}, 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        user_id = session["user_id"]

        cursor.execute(
            "SELECT cash_balance FROM users WHERE user_id = %s FOR UPDATE",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            connection.rollback()
            return {"status": "error", "message": "User not found"}, 404

        cursor.execute(
            "SELECT stock_id, current_price FROM stocks WHERE stock_id = %s",
            (stock_id,)
        )
        stock = cursor.fetchone()

        if not stock:
            connection.rollback()
            return {"status": "error", "message": "Stock not found"}, 404

        price = stock["current_price"]
        total = price * shares

        if user["cash_balance"] < total:
            connection.rollback()
            return {"status": "error", "message": "Insufficient funds"}, 400

        cursor.execute("""
            UPDATE users
            SET cash_balance = cash_balance - %s
            WHERE user_id = %s
        """, (total, user_id))

        cursor.execute("""
            INSERT INTO holdings (user_id, stock_id, share_num)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE share_num = share_num + %s
        """, (user_id, stock_id, shares, shares))

        cursor.execute("""
            INSERT INTO transactions
                (user_id, stock_id, transaction_type,
                 share_num, price, total_amount)
            VALUES (%s, %s, 'BUY', %s, %s, %s)
        """, (user_id, stock_id, shares, price, total))

        connection.commit()

        return {
            "status": "success",
            "message": f"Successfully purchased {shares} shares",
            "total": float(total)
        }

    except Exception:
        if connection is not None:
            connection.rollback()
        app.logger.exception("Failed to buy stock")
        return {"status": "error", "message": "Unable to complete purchase"}, 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

##Sell stock route
@app.route("/api/sell", methods=["POST"])
def sell_stock():

    if "user_id" not in session:
        return {"status": "error", "message": "Please log in first"}, 401

    data = request.get_json(silent=True) or {}

    try:
        stock_id = int(data.get("stock_id"))
        shares = int(data.get("shares"))
        if stock_id <= 0 or shares <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return {"status": "error", "message": "Invalid stock or share amount"}, 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        connection.start_transaction()

        user_id = session["user_id"]

        cursor.execute(
            "SELECT cash_balance FROM users WHERE user_id = %s FOR UPDATE",
            (user_id,)
        )
        user = cursor.fetchone()

        if not user:
            connection.rollback()
            return {"status": "error", "message": "User not found"}, 404

        cursor.execute("""
            SELECT share_num
            FROM holdings
            WHERE user_id = %s AND stock_id = %s
            FOR UPDATE
        """, (user_id, stock_id))

        holding = cursor.fetchone()

        if not holding or holding["share_num"] < shares:
            connection.rollback()
            return {"status": "error", "message": "Not enough shares to sell"}, 400

        cursor.execute(
            "SELECT current_price FROM stocks WHERE stock_id = %s",
            (stock_id,)
        )
        stock = cursor.fetchone()

        if not stock:
            connection.rollback()
            return {"status": "error", "message": "Stock not found"}, 404

        price = stock["current_price"]
        total = price * shares

        cursor.execute("""
            UPDATE holdings
            SET share_num = share_num - %s
            WHERE user_id = %s AND stock_id = %s
        """, (shares, user_id, stock_id))

        cursor.execute("""
            DELETE FROM holdings
            WHERE user_id = %s AND stock_id = %s AND share_num = 0
        """, (user_id, stock_id))

        cursor.execute("""
            UPDATE users
            SET cash_balance = cash_balance + %s
            WHERE user_id = %s
        """, (total, user_id))

        cursor.execute("""
            INSERT INTO transactions
                (user_id, stock_id, transaction_type,
                 share_num, price, total_amount)
            VALUES (%s, %s, 'SELL', %s, %s, %s)
        """, (user_id, stock_id, shares, price, total))

        connection.commit()

        return {
            "status": "success",
            "message": f"Successfully sold {shares} shares",
            "total": float(total)
        }

    except Exception:
        if connection is not None:
            connection.rollback()
        app.logger.exception("Failed to sell stock")
        return {"status": "error", "message": "Unable to complete sale"}, 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

##Deposit Cash Route
from decimal import Decimal, InvalidOperation

@app.route("/api/deposit", methods=["POST"])
def deposit_cash():
    if "user_id" not in session:
        return {"status": "error", "message": "Please log in first"}, 401

    data = request.get_json(silent=True) or {}

    try:
        amount = Decimal(str(data.get("amount")))
        if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
            raise ValueError()
    except (InvalidOperation, ValueError, TypeError):
        return {"status": "error", "message": "Invalid deposit amount"}, 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            UPDATE users
            SET cash_balance = cash_balance + %s
            WHERE user_id = %s
        """, (amount, session["user_id"]))

        if cursor.rowcount != 1:
            connection.rollback()
            return {"status": "error", "message": "User not found"}, 404

        connection.commit()

        return {
            "status": "success",
            "message": "Deposit successful"
        }

    except Exception:
        if connection is not None:
            connection.rollback()
        app.logger.exception("Failed to deposit cash")
        return {"status": "error", "message": "Unable to deposit cash"}, 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

##Withdraw Cash Route
@app.route("/api/withdraw", methods=["POST"])
def withdraw_cash():
    if "user_id" not in session:
        return {"status": "error", "message": "Please log in first"}, 401

    data = request.get_json(silent=True) or {}

    try:
        amount = Decimal(str(data.get("amount")))
        if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
            raise ValueError()
    except (InvalidOperation, ValueError, TypeError):
        return {"status": "error", "message": "Invalid withdrawal amount"}, 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            UPDATE users
            SET cash_balance = cash_balance - %s
            WHERE user_id = %s AND cash_balance >= %s
        """, (amount, session["user_id"], amount))

        if cursor.rowcount != 1:
            connection.rollback()
            return {
                "status": "error",
                "message": "Insufficient funds or account not found"
            }, 400

        connection.commit()

        return {
            "status": "success",
            "message": "Withdrawal successful"
        }

    except Exception:
        if connection is not None:
            connection.rollback()
        app.logger.exception("Failed to withdraw cash")
        return {"status": "error", "message": "Unable to withdraw cash"}, 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()

##Admin Stock functionality
@app.route("/api/admin/stocks", methods=["POST"])
def admin_create_stock():

    if "user_id" not in session or session.get("role") != "admin":
        return {"status": "error", "message": "Admin access required"}, 403

    data = request.get_json(silent=True) or {}

    ticker = str(data.get("ticker", "")).strip().upper()
    company_name = str(data.get("company_name", "")).strip()

    try:
        available_shares = int(data.get("available_shares"))
        initial_price = Decimal(str(data.get("initial_price")))

        if (not ticker or not company_name or
            available_shares <= 0 or
            not initial_price.is_finite() or
            initial_price <= 0 or
            initial_price.as_tuple().exponent < -2):
            raise ValueError()

    except (ValueError, TypeError, InvalidOperation):
        return {"status": "error", "message": "Invalid stock information"}, 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO stocks
                (ticker, company_name, current_price,
                 opening_price, day_high, day_low, available_shares)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            ticker, company_name, initial_price,
            initial_price, initial_price, initial_price,
            available_shares
        ))

        connection.commit()

        return {
            "status": "success",
            "message": f"Stock {ticker} created successfully"
        }, 201

    except mysql.connector.IntegrityError:
        if connection is not None:
            connection.rollback()
        return {"status": "error", "message": "Stock ticker already exists"}, 409

    except Exception:
        if connection is not None:
            connection.rollback()
        app.logger.exception("Failed to create stock")
        return {"status": "error", "message": "Unable to create stock"}, 500

    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    app.run(debug=True)

