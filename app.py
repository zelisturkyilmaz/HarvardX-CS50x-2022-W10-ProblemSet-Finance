import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Remember who signed in
    id = session["user_id"]


    portfolio = db.execute("SELECT history.user_id, symbol, SUM(shares), cash FROM history INNER JOIN users ON users.id = history.user_id WHERE history.user_id = ? GROUP BY history.user_id;", id)

    rows = db.execute("SELECT * FROM users WHERE id = ?",
                          id)

    # Return to summary
    if len(portfolio) == 0:
        return render_template("index.html", cash=rows[0]["cash"], sum_total=rows[0]["cash"])

    if portfolio[0]["SUM(shares)"] == 0:
        return render_template("index.html", cash=rows[0]["cash"], sum_total=rows[0]["cash"])


    return render_template("index.html", portfolio=portfolio, name=lookup(portfolio[0]["symbol"])["name"], price=lookup(portfolio[0]["symbol"])["price"], total=lookup(portfolio[0]["symbol"])["price"] * portfolio[0]["SUM(shares)"], cash=portfolio[0]["cash"], sum_total=portfolio[0]["cash"] + lookup(portfolio[0]["symbol"])["price"] * portfolio[0]["SUM(shares)"])


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        symbol = request.form.get("symbol")
        try:
            shares = int(request.form.get("shares"))
        except ValueError:
            return apology("shares must be a posative integer", 400)


        # Ensure symbol area is not empty
        if not symbol:
            return apology("must enter a character", 400)

        # Ensure shares area is not empty and it is a positive integer
        if not shares > 0:
            return apology("must enter a positive number", 400)

        # If symbol doesn't exist, return apology page
        if lookup(symbol) == None:
            return apology("symbol doesn't exist", 400)

        # Remember the id of which user has logged in
        id = session["user_id"]

        # Find the current user's cash
        rows = db.execute("SELECT * FROM users WHERE id = ?",
                          id)

        cash = rows[0]["cash"]

        # If symbol exist, find price
        price = lookup(symbol)["price"]


        # Check if the user has enough cash for the transaction
        if not cash >= price*shares:
            return apology("cannot afford the number of shares at the current price", 403)

        else:
                # Time of transaction
                time = datetime.now()

                # Save transaction to history database
                db.execute("INSERT INTO history (user_id, symbol, price, shares, time) VALUES (?, ?, ?, ?, ?)", id, symbol, price, shares, time)

                # Update cash
                cash = cash - (price * shares)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, id)

                portfolio = db.execute("SELECT history.user_id, symbol, SUM(shares), cash FROM history INNER JOIN users ON users.id = history.user_id WHERE history.user_id = ? GROUP BY history.user_id;", id)


                # Return to summary
                return render_template("index.html", portfolio=portfolio, name=lookup(symbol)["name"], price=lookup(symbol)["price"], total=lookup(symbol)["price"] * portfolio[0]["SUM(shares)"], cash=portfolio[0]["cash"], sum_total=portfolio[0]["cash"] + lookup(portfolio[0]["symbol"])["price"] * portfolio[0]["SUM(shares)"])

    # User reached route via GET
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    id = session["user_id"]

    portfolio = db.execute("SELECT * FROM history WHERE user_id = ? ORDER BY time ASC", id)

    return render_template("history.html", portfolio=portfolio)


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
        rows = db.execute("SELECT * FROM users WHERE username = ?",
                          request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        symbol = request.form.get("symbol")

        # Ensure search area is not empty
        if not symbol:
            return apology("must enter a character", 400)

        # If symbol doesn't exist, return apology page
        if lookup(symbol) == None:
            return apology("symbol doesn't exist", 400)

        # If symbol exist, return dictionary values
        else:
            return render_template("quoted.html", symbol=lookup(symbol))

    # User reached route via GET
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):

            return apology("must provide password", 400)

        # Ensure password confirmation was submitted
        elif not request.form.get("password"):
            return apology("must confirm password", 400)

        # Ensure password matches with confirmation of password
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("Passwords doesn't match", 400)

        # Ensure username doesn't exists
        elif len(db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))) != 0:
            return apology("try a different username", 400)

        # Save it to Database
        else:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", request.form.get(
                "username"), generate_password_hash(request.form.get("password")))

        # Remember which user has logged in
        session["user_id"] = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username"))[0]["id"]

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # Remember who signed in
    id = session["user_id"]

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))

        # Ensure symbol area is not empty
        if not symbol or symbol == "Symbol":
            return apology("must choose a symbol", 400)

        # Ensure shares area is not empty and it is a positive integer
        if not shares > 0:
            return apology("must enter a positive number", 400)

        portfolio = db.execute(
                "SELECT history.user_id, symbol, SUM(shares), cash FROM history INNER JOIN users ON users.id = history.user_id WHERE history.user_id = ? GROUP BY history.user_id;", id)

        total_shares = portfolio[0]["SUM(shares)"]

        price = lookup(symbol)["price"]
        cash = portfolio[0]["cash"]

        if total_shares < shares:
            return apology("Don't have enough shares to sell", 400)

        else:
            # Time of transaction
            time = datetime.now()

            # Save transaction to history database
            db.execute("INSERT INTO history (user_id, symbol, price, shares, time) VALUES (?, ?, ?, ?, ?)",
                       id, symbol, price, 0-shares, time)

            # Update cash
            cash = cash + (price * shares)
            db.execute("UPDATE users SET cash = ? WHERE id = ?", cash, id)

            stocks = db.execute(
                   "SELECT history.user_id, symbol, SUM(shares), cash FROM history INNER JOIN users ON users.id = history.user_id WHERE history.user_id = ? GROUP BY history.user_id;", id)

            if len(stocks) == 0:
                return render_template("index.html", cash=cash, sum_total=cash)

            if stocks[0]["SUM(shares)"] == 0:
                return render_template("index.html", cash=cash, sum_total=cash)

            # Return to summary
            return render_template("index.html", portfolio=stocks, name=lookup(symbol)["name"], price=lookup(symbol)["price"], total=lookup(symbol)["price"] * stocks[0]["SUM(shares)"], cash=stocks[0]["cash"], sum_total=stocks[0]["cash"] + lookup(stocks[0]["symbol"])["price"] * stocks[0]["SUM(shares)"])

    else:
        stocks = db.execute("SELECT history.user_id, symbol, SUM(shares), cash FROM history INNER JOIN users ON users.id = history.user_id WHERE history.user_id = ? GROUP BY history.user_id;", id)

        if stocks[0]["SUM(shares)"] == 0:
            return render_template("sell.html")
        return render_template("sell.html", portfolio=stocks)
