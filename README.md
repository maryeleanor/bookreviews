# Bookreads

##<a href="https://docs.cs50.net/web/2020/x/projects/1/project1.html" target="_blank" style="font-weight:bold;">Project 1</a> for CS50 Web Programming with Python and JavaScript

---

This is a bookclub web app built with python, flask and PostgreSQL to search for and review books. The database contains 5,000 books to search through, and the ratings and number of reviews are pulled in from the Goodreads API.

Users can also access our book details via a custom API. 
If users make a GET request to the website’s /api/<isbn> route, where <isbn> is a 10 digi ISBN number, we return a JSON response containing the book’s title, author, publication date, ISBN number, review count, and average score.  
   

Check it out on heroku  <a href="https://books-maryeleanor.herokuapp.com/" target="_blank" style="font-weight:bold;">here.</a>