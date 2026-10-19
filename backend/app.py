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


## route for account.html to get the logged-in user's info
@app.route("/api/me")
def current_user():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT user_id, full_name, username, email, role
        FROM users
        WHERE user_id = %s
        """,
        (session["user_id"],)
    )

    user = cursor.fetchone()

    cursor.close()
    connection.close()

    return user

##route for logout button
@app.route("/api/logout")
def logout():
    session.clear()
    return redirect("/frontend/index.html")


    #### view stock ticker function by melody
@app.route("/api/stocks", methods=["GET"])
def get_stocks():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT ticker, company_name, current_price,
                   opening_price, day_high, day_low
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
            SELECT ticker, company_name, current_price,
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

### admin creation stock 

### admin creation stock - bryan
@app.route("/api/admin/stocks", methods=["POST"])
def create_stock():

    if "user_id" not in session:
        return "You must be logged in.", 401

    if session.get("role") != "admin":
        return "Admin access required.", 403

    ticker = request.form.get("ticker")
    company_name = request.form.get("company_name")
    available_shares = request.form.get("volume")
    initial_price = request.form.get("initial_price")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO stocks
            (
                ticker,
                company_name,
                available_shares,
                current_price,
                opening_price,
                day_high,
                day_low
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                ticker.upper(),
                company_name,
                available_shares,
                initial_price,
                initial_price,
                initial_price,
                initial_price
            )
        )

        connection.commit()

    except mysql.connector.IntegrityError:
        cursor.close()
        connection.close()
        return "That ticker already exists.", 409

    cursor.close()
    connection.close()

    return redirect("/frontend/stocks.html")


if __name__ == "__main__":
    app.run(debug=True)