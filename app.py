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


def search(book):
    book = "%{}%".format(book)
    books = db.execute("SELECT * FROM books WHERE isbn ILIKE :book OR title ILIKE :book OR author ILIKE :book ORDER BY year DESC", {
        "book": book}).fetchall()

    if not books:
        books_result = None
        return books_result

    goodreads = []
    for book in books:
            res = requests.get("https://www.goodreads.com/book/review_counts.json",
                               params={"key": "DchANaDeTrPFG7BRpUBZIw", "isbns": book.isbn})
            result = res.json()
            goodreads.append(result['books'])

    books_result = zip(books, goodreads)
    return books_result


def book_reviews(book_id):
    book = db.execute(
        "SELECT * FROM books WHERE id = :book_id", {
            "book_id": book_id}).fetchone()

    reviews = db.execute(
        "SELECT * FROM reviews WHERE book_id = :book_id", {
            "book_id": book.id}).fetchall()

    usernames = []
    for review in reviews:
        user = db.execute("SELECT * FROM users WHERE id = :id",
                    {"id": review.user_id}).fetchone()
        usernames.append(user.username.capitalize())

    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "DchANaDeTrPFG7BRpUBZIw", "isbns": book.isbn})
    result = res.json()
    goodreads_book = result['books']
    ratings = (float(goodreads_book[0]['average_rating'])/5) * 100
     
    if session.get("user_id") is None:
        current_user = 0;
    else:
        user = db.execute("SELECT * FROM users WHERE id = :id",
                        {"id": session["user_id"]}).fetchall()
        current_user = user[0].username.capitalize()

    review_input = True
    for name in usernames:
        if name == current_user:
            review_input = False

    review_results = zip(reviews, usernames)
    return book, review_results, goodreads_book, ratings, review_input, current_user


@app.route("/", methods=["GET", "POST"])
def index():
    # if user clicked search
    if request.method == "POST":
        book = request.form.get("book") 

        # was a search term entered? 
        if not book:
            return apology("must provide a book to search for", 404)

        # query db and goodreads for search term
        books_result = search(book)

        # if no result, return no match
        if not books_result:
            no_match = "Sorry, no books found. Try another search"
            return render_template('index.html', no_match=no_match)

        # otherwise display results
        return render_template('index.html', books_result=books_result)

    else:
        # render search homepage
        return render_template('index.html')



@app.route('/book/<int:book_id>', methods=['GET', 'POST'])
def book(book_id):
    if request.method == "POST":
        review = request.form["review"]
        try:
            rating = int(request.form['options'])
        except:
            rating = None  

        if not review and not rating:
            return apology("you didn't provide a rating or review", 404)

        # check if user has already reviewed this book, if so send them to update review
        reviews = db.execute("SELECT * FROM reviews WHERE user_id = :user_id", {
            "user_id": session["user_id"]}).fetchone()
      
        if reviews:
            db.execute("UPDATE reviews (:review, :rating) WHERE id = :id", {
                "review": review, "rating": rating, "id": reviews.id})
        
        else:
            # otherwise submit review into db
            db.execute("INSERT INTO reviews (review, rating, book_id, user_id) VALUES (:review, :rating, :book_id, :user_id)", {
                    "review": review, "rating": rating, "book_id": book_id, "user_id": session["user_id"]})
            db.commit()

    # query db for this book's details and render page
    b, rr, gr, r, ri, cu = book_reviews(book_id)
    return render_template('book.html', book=b, review_results=rr, goodreads_book=gr, ratings=r, review_input=ri, current_user=cu)


@app.route('/review/<int:review_id>', methods=['GET', 'POST'])
def review(review_id):
    reviews = db.execute("SELECT * FROM reviews WHERE id = :review_id", {
        "review_id": review_id}).fetchone()
    book_id = reviews.book_id

    if request.method == "POST":
        if request.form['action'] == 'delete':
            db.execute("DELETE FROM reviews WHERE id = id", {
                "id": review_id})
            db.commit()
        
        if request.form['action'] == 'update':
            review = request.form["review"]
            
            try:
                rating = int(request.form['options'])
            except:
                rating = None

            if not review:
                db.execute("UPDATE reviews SET rating = :rating WHERE id = :id", {
                    "rating": rating, "id": review_id})

            elif rating == None: 
                db.execute("UPDATE reviews SET review = :review WHERE id = :id", {
                "review": review, "id": review_id})

            else:        
                db.execute("UPDATE reviews SET review = :review, rating= :rating WHERE id = :id", {
                    "review": review, "rating": rating, "id": review_id})

            db.commit()

        # query db for this book's details and render page
        b, rr, gr, r, ri, cu = book_reviews(book_id)
        return render_template('book.html', book=b, review_results=rr, goodreads_book=gr, ratings=r, review_input=ri, current_user=cu)

    else:
        # query db for this book's details and render page
        b, rr, gr, r, ri, cu = book_reviews(book_id)
        return render_template('review.html', book=b, review_results=rr, goodreads_book=gr, ratings=r, review_input=ri, current_user=cu)



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # if user submited a form via POST)
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

        # Ensure username is not taken 
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
