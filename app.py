import os
import requests
import json
from functools import wraps
from flask import Flask, session, flash, jsonify, redirect, render_template, request, session, url_for
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Check for environment variable
# db URI postgres://gxorncbjrcfvfb:4d8d52cccd8f9632ef389a6aedf4cd530dc683f5de08abff236c3c82af0089d8@ec2-34-193-232-231.compute-1.amazonaws.com:5432/d7v3iiv0ofav9c
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# Goodreads API key and secret
# key: DchANaDeTrPFG7BRpUBZIw
# secret: t5VRb1Uf3nJXZeb489i5Y4HkIuADwEV0nEtbjcxhnd4



def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/register")
        return f(*args, **kwargs)
    return decorated_function


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        book = request.form.get("book") 
        search = "%{}%".format(book)
        books = db.execute(
            "SELECT * FROM books WHERE isbn ILIKE :book OR title ILIKE :book OR author ILIKE :book ORDER BY year DESC", {"book":search}).fetchall()
        # books.append({'ratings_count':''})  
        # books.append({'reviews_count': ''})
        # books.append({'average_rating': ''})
        for book in books:
            isbn = book.isbn
            res = requests.get("https://www.goodreads.com/book/review_counts.json",
                           params={"key": "DchANaDeTrPFG7BRpUBZIw", "isbns": isbn})
            json_result=res.json() 
            goodreads = json_result['books']
            # book.ratings_count = goodreads['ratings_count']
            # book.reviews_count = goodreads['reviews_count']
            # book.average_ratings = goodreads['average_ratings']
        return render_template('index.html', books=books, goodreads=goodreads)

    else:
        user = db.execute("SELECT * FROM users WHERE id = :id", {"id":session["user_id"]}).fetchall()
        username = user[0].username.capitalize()
        return render_template('index.html', username=username)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")

        # Ensure username was submitted
        if not username:
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 403)

        # Query database for username
        check = db.execute("SELECT * FROM users WHERE username = :username", {"username":username}).fetchall()

        # Ensure username exists and password is correct
        if len(check) != 0:
            return apology("that username is taken", 403)

        # Hash pw
        hash = generate_password_hash(request.form.get(
            "password"), method='pbkdf2:sha256', salt_length=8)

        # Add new user to db
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", {"username":username, "hash":hash})
        db.commit()

        # Redirect user to login
        return render_template("login.html", account="Great, your account was created.")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")
        
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", {"username":username}).fetchall()

        # Ensure username exists and password is correct
        if not rows or not check_password_hash(rows[0]["hash"], request.form.get("password")):
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

