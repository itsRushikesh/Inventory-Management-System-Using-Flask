from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
import MySQLdb.cursors
  

from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
 
app = Flask(__name__)
app.secret_key = "Cairocoders-Ednalan"
  
   

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'testingdb'
app.config['MYSQL_HOST'] = 'localhost'

mysql = MySQL(app)

# mysql.init_app(app)
  
# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')
 
# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])
  
# Index
@app.route('/')
def index():
    return render_template('home.html')
  
# About
@app.route('/about')
def about():
    return render_template('about.html')
 
# Articles
@app.route('/articles')
def articles():
    # Create cursor
    # conn = pymysql.connect()
    # cur = conn.cursor(pymysql.cursors.DictCursor)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
  
    # Get articles
    result = cursor.execute("SELECT * FROM articles")
    articles = cursor.fetchall()
    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)
    # Close connection
    cursor.close()
 
#Single Article
@app.route('/article/<string:id>/')
def article(id):
    # Create cursor
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
    # Get article
    result = cursor.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cursor.fetchone()
    return render_template('article.html', article=article)
  
# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
          
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        # Create a new record
        cursor.execute("INSERT INTO `user_flask` (name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

                
        # Commit to DB
        mysql.connection.commit()
        # Close connection
        cursor.close()
        flash('You are now registered and can log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)
 
# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
        # Get user by username
        result = cursor.execute("SELECT * FROM user_flask WHERE username = %s", [username])
  
        if result > 0:
            # Get stored hash
            data = cursor.fetchone()
            password = data['password']
  
            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username
  
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cursor.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)
  
    return render_template('login.html')
 
# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap
 
# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))
  
# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    # Create cursor
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
    # Get articles
    #result = cur.execute("SELECT * FROM articles")
    # Show articles only from the user logged in 
    result = cursor.execute("SELECT * FROM articles WHERE author = %s", [session['username']])
  
    articles = cursor.fetchall()
  
    if result > 0:
        return render_template('dashboard.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cursor.close()
 
# Add Article
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data
  
        # Create Cursor
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
        # Execute
        cursor.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",(title, body, session['username']))
        # Commit to DB
        mysql.connection.commit()
        #Close connection
        cursor.close()
        flash('Article Created', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)
 
# Edit Article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # Create cursor
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
    # Get article by id
    result = cursor.execute("SELECT * FROM articles WHERE id = %s", [id])
    article = cursor.fetchone()
    cursor.close()
    # Get form
    form = ArticleForm(request.form)
    # Populate article form fields
    form.title.data = article['title']
    form.body.data = article['body']
  
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']
        # Create Cursor
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        app.logger.info(title)
        # Execute
        cursor.execute ("UPDATE articles SET title=%s, body=%s WHERE id=%s",(title, body, id))
        # Commit to DB
        mysql.connection.commit()
        #Close connection
        cursor.close()
        flash('Article Updated', 'success')
        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)
  
  
# Delete Article
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # Create cursor
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
    # Execute
    cursor.execute("DELETE FROM articles WHERE id = %s", [id])
    # Commit to DB
    mysql.connection.commit
    #Close connection
    cursor.close()
    flash('Article Deleted', 'success')
    return redirect(url_for('dashboard'))
  
if __name__ == '__main__':
 app.run(debug=True)