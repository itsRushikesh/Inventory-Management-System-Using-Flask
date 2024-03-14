from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
import MySQLdb.cursors
from wtforms import Form, StringField, PasswordField, validators, SelectField, IntegerField, EmailField
from wtforms.validators import Length, Regexp
from passlib.hash import sha256_crypt
from functools import wraps
 
app = Flask(__name__)
app.secret_key = "Cairocoders-Ednalan"
  
   

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'testingdb'
app.config['MYSQL_HOST'] = 'localhost'

mysql = MySQL(app)

  

role_list = ['Engineer', 'Manager']
class RegisterForm(Form):
    role = SelectField('Role',choices=role_list)
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = EmailField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [validators.DataRequired(),
        validators.Length(min=8, max=15, message='Password must be between 8 and 15 characters'),
        validators.Regexp('^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,15}$',
               message='Password must contain at least one symbol, one uppercase letter, one lowercase letter, and one number'),                               
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')
 
# asset Form Class
class InventoryForm(Form):
    name = StringField('name', [validators.Length(min=1, max=200)])
    quantity = IntegerField('quantity')
  
# Index
@app.route('/')
def index():
    return render_template('home.html')
  
# About
@app.route('/about')
def about():
    return render_template('about.html')
 
# assets
@app.route('/assets')
def assets():
    # Create cursor
    # conn = pymysql.connect()
    # cur = conn.cursor(pymysql.cursors.DictCursor)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
  
    # Get assets
    result = cursor.execute("SELECT * FROM assets")
    assets = cursor.fetchall()
    if result > 0:
        return render_template('assets.html', assets=assets)
    else:
        msg = 'No assets Found'
        return render_template('assets.html', msg=msg)
    # Close connection
    cursor.close()
 
#Single asset
@app.route('/asset/<string:id>/')
def asset(id):
    # Create cursor
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    # Get asset
    cursor.execute("SELECT * FROM assets WHERE id = %s", [id])
    asset = cursor.fetchone()
    
    return render_template('asset.html', asset=asset)
  
# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        role = form.role.data
          
        
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        check_user_exist = cursor.execute("SELECT * FROM accounts WHERE username = %s or email = %s",(username,email))
        if check_user_exist > 0:
            flash('user already exist','danger')
        else:
            # Create a new record
            cursor.execute("INSERT INTO `accounts` (name, email, username, password, role) VALUES(%s, %s, %s, %s, %s)", (name, email, username, password, role))

                    
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
        role_candidate = request.form['role']
        username = request.form['username']
        password_candidate = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
        # Get user by username
        result = cursor.execute("SELECT * FROM accounts WHERE username = %s", [username])
  
        if result > 0:
            # Get stored hash
            data = cursor.fetchone()
            role = data['role']
            password = data['password']
  
            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password) and role_candidate == role:
                # Passed
                session['logged_in'] = True
                session['role'] = role
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
  
    # Get assets
    #result = cur.execute("SELECT * FROM assets")
    # Show assets only from the user logged in 
    result = cursor.execute("SELECT * FROM assets WHERE user = %s", [session['username']])
  
    assets = cursor.fetchall()
  
    if result > 0:
        return render_template('dashboard.html', assets=assets)
    else:
        msg = 'No assets Found'
        return render_template('dashboard.html', msg=msg)
    # Close connection
    cursor.close()
 
# Add asset
@app.route('/add_asset', methods=['GET', 'POST'])
@is_logged_in
def add_asset():
    form = InventoryForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        quantity = form.quantity.data
  
        # Create Cursor
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
        # Execute
        check_asset = cursor.execute("SELECT * FROM assets WHERE name = %s",[name])
        # data = cursor.fetchall()
        if check_asset >  0:
            cursor.execute("SELECT quantity FROM assets WHERE name = %s",[name])
            qty = cursor.fetchone()
            print(qty)
            qty1 = (qty['quantity'])
            new_qty = qty1 + quantity
            cursor.execute("UPDATE assets SET quantity = %s WHERE name = %s",(new_qty, name))
            # Commit to DB
            mysql.connection.commit()
            #Close connection
            cursor.close()
            flash('asset updated', 'success')
            return redirect(url_for('dashboard'))
        else:
            cursor.execute("INSERT INTO assets(name, quantity, user) VALUES(%s, %s, %s)",(name, quantity, session['username']))
            # Commit to DB
            mysql.connection.commit()
            #Close connection
            cursor.close()
            flash('asset Created', 'success')
            return redirect(url_for('dashboard'))
    return render_template('add_asset.html', form=form)
 
# Edit asset
@app.route('/edit_asset/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_asset(id):
    # Create cursor
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
    # Get asset by id
    result = cursor.execute("SELECT * FROM assets WHERE id = %s", [id])
    asset = cursor.fetchone()
    cursor.close()
    # Get form
    form = InventoryForm(request.form)
    # Populate asset form fields
    form.name.data = asset['name']
    form.quantity.data = asset['quantity']
  
    if request.method == 'POST' and form.validate():
        name = request.form['name']
        quantity = request.form['quantity']
        # Create Cursor
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        app.logger.info(name)
        #check asset
        check_asset = cursor.execute("SELECT * FROM assets WHERE name = %s",[name])
        # data = cursor.fetchall()
        if check_asset >  0:
            flash('asset already exist')
        # Execute
        else:
            cursor.execute ("UPDATE assets SET name=%s, quantity=%s WHERE id=%s",(name, quantity, id))
            # Commit to DB
            mysql.connection.commit()
            #Close connection
            cursor.close()
            flash('asset Updated', 'success')
            return redirect(url_for('dashboard'))
    return render_template('edit_asset.html', form=form)
  
  
# Delete asset
@app.route('/delete_asset/<string:id>', methods=['POST'])
@is_logged_in
def delete_asset(id):
    # Create cursor
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
    # Execute
    cursor.execute("DELETE FROM assets WHERE id = %s", [id])
    # Commit to DB
    mysql.connection.commit
    #Close connection
    cursor.close()
    flash('asset Deleted', 'success')
    return redirect(url_for('dashboard'))
  
if __name__ == '__main__':
 app.run(debug=True)