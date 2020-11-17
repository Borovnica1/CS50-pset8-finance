import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    userid = session["user_id"]
    username = db.execute("SELECT username FROM users WHERE id=(?)", (userid))[0]["username"]
    cash = db.execute("SELECT cash FROM users WHERE id=(?)", (userid))[0]["cash"]
    print(username)
    stocks = db.execute("SELECT stock, SUM(stocks) stocks FROM transactions WHERE username=(?) GROUP BY stock", (username))
    stocksToDelete = []
    print(stocks)
    userTotal = cash
    for stock in stocks:
        print(stock)
        symbol = stock["stock"]
        stockObj = lookup(symbol)
        name = stockObj["name"]
        price = stockObj["price"]
        total = price * stock["stocks"]
        stock["price"] = usd(price)
        stock["total"] = usd(total)
        stock["name"] = name
        userTotal += total
        if stock["stocks"] == 0:
            print('lol')
            stocksToDelete.append(stock)
    for stock in stocksToDelete:
        stocks.remove(stock)
    print(stocks)
    print(cash)
    return render_template("index.html", stocks=stocks, cash=usd(cash), userTotal=usd(userTotal))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        stocks = request.form.get("shares")
        price = lookup(symbol)["price"]
        userid = session["user_id"]
        print(price, stocks)
        costOfStocks = price * float(stocks)
        """db.execute("INSERT INTO transactions (username, hash) VALUES (:username, :password)", username=username, password=password)"""
        userCash = db.execute("SELECT cash FROM users WHERE id=(?)", (userid))[0]["cash"]
        username = db.execute("SELECT username FROM users WHERE id=(?)", (userid))[0]["username"]
        print(userid, userCash, costOfStocks, username)
        if not request.form.get("symbol"):
            return apology("must provide correct symbol share", 403)
        elif not request.form.get("shares"):
            return apology("must provide number of shares", 403)
        elif userCash - costOfStocks > 0:
            print('can trade')
            db.execute("INSERT INTO transactions (username, stocks, stock, cost) VALUES (:username, :stocks, :symbol, :costOfStocks)", username=username, stocks=stocks, symbol=symbol, costOfStocks=costOfStocks)
            db.execute("UPDATE users SET cash=(?) WHERE id=(?)", (userCash - costOfStocks, userid))
            return redirect("/")
        else:
            return apology("Sorry you dont have sufficent funds", 403)



    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        print(rows)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        print(rows[0]["id"])

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        result = lookup(symbol)
        print(result)
        msg = f'{symbol} is not a legit share'
        if not result:
            return apology(msg, 403)
        else:
            return render_template("quoted.html", result=result)


    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif request.form.get("confirmation") != request.form.get("password"):
            return apology("must confirm password", 403)
        else:
            username = request.form.get("username")
            password = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username, hash) VALUES (:username, :password)", username=username, password=password)
            return redirect("/")

    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    if request.method == "GET":
        userid = session["user_id"]
        username = db.execute("SELECT username FROM users WHERE id=(?)", (userid))[0]["username"]
        stocks = db.execute("SELECT stock, SUM(stocks) FROM transactions WHERE username=(?) GROUP BY stock", (username))
        print(stocks)
        for stock in stocks:
            if stock["SUM(stocks)"] == 0:
                print('lol')
                stocks.remove(stock)
        return render_template("sell.html", names=stocks)
    else:
        symbol = request.form.get("symbol")
        stocks = request.form.get("shares")
        price = lookup(symbol)["price"]
        userid = session["user_id"]
        print(price, stocks)
        costOfStocks = price * float(stocks)
        userCash = db.execute("SELECT cash FROM users WHERE id=(?)", (userid))[0]["cash"]
        username = db.execute("SELECT username FROM users WHERE id=(?)", (userid))[0]["username"]
        userStocks = db.execute("SELECT SUM(stocks) FROM transactions WHERE username=(?) AND stock=(?) GROUP BY stock", (username, symbol))[0]["SUM(stocks)"]
        print(userid, userCash, costOfStocks, username, userStocks)
        if not request.form.get("symbol"):
            return apology("must provide correct symbol share", 403)
        elif not request.form.get("shares"):
            return apology("must provide number of shares", 403)
        elif userStocks >= int(stocks):
            print('can sell')
            db.execute("INSERT INTO transactions (username, stocks, stock, cost) VALUES (:username, :stocks, :symbol, :costOfStocks)", username=username, stocks='-'+stocks, symbol=symbol, costOfStocks=costOfStocks)
            db.execute("UPDATE users SET cash=(?) WHERE id=(?)", (userCash + costOfStocks, userid))
            return redirect("/")
        else:
            return apology("Sorry you dont have that many stocks", 403)



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
