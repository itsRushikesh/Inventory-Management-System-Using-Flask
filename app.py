from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from flask_mysqldb import MySQL
import MySQLdb.cursors
from wtforms import Form, StringField,PasswordField,FileField, validators, SelectField, IntegerField, EmailField
from wtforms.validators import Length, Regexp
from flask_wtf import FlaskForm
from passlib.hash import sha256_crypt
from functools import wraps
import os
from werkzeug.utils import secure_filename
import logging


UPLOAD_FOLDER = 'uploads'
# ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'} 
app = Flask(__name__)
app.secret_key = "Cairocoders-Ednalan"
  
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '123456'
app.config['MYSQL_DB'] = 'testingdb'
app.config['MYSQL_HOST'] = 'localhost'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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
    file = FileField()
    confirm = PasswordField('Confirm Password')

class InventoryForm(Form):
    name = StringField('name', [validators.Length(min=1, max=200)])
    quantity = IntegerField('quantity')
    file = FileField('file')
  
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

#register2
@app.route('/register2', methods = ['GET', 'POST'])
def register2():
    return render_template('register.html')

@app.route('/login2', methods = ['GET', 'POST'])
# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email   = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        role = form.role.data   
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        check_user_acc = cursor.execute("SELECT * FROM accounts WHERE username = %s or email = %s",(username,email))
        check_user_req = cursor.execute("SELECT * FROM request  WHERE username = %s or email = %s",(username,email))
        if check_user_acc > 0:
            flash('User already registered','danger')
        elif check_user_req>0:
            flash('User request has already sent','danger')
        else:
            # Create a new record
            cursor.execute("INSERT INTO `request` (name, email, username, password, role) VALUES(%s, %s, %s, %s, %s)", (name, email, username, password, role))    
            # Commit to DB
            mysql.connection.commit()
            # Close connection
            cursor.close()
            flash('Request has been sent to admin', 'success')
            return redirect(url_for('login'))
    return render_template('register.html', form=form)
 
# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
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
            if sha256_crypt.verify(password_candidate, password):
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
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if session['role'] == 'admin':
        result = cursor.execute("SELECT * FROM assets")
    else:
        result = cursor.execute("SELECT * FROM assets WHERE user = %s", [session['username']])
        
    assets = cursor.fetchall()
    
    result2 = cursor.execute("SELECT * FROM request WHERE status = 'pending'")
    requests = cursor.fetchall()
   
    if result > 0 or result2 > 0:
        return render_template('dashboard.html', assets=assets, requests = requests)
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
        file = request.files['file']
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
            if file.filename == '':
                flash('No selected file')
                return redirect(url_for('add_asset'))
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('asset updated', 'success')
            return redirect(url_for('dashboard'))
        else:
            cursor.execute("INSERT INTO assets(name, quantity, user) VALUES(%s, %s, %s)",(name, quantity, session['username']))
            # Commit to DB
            mysql.connection.commit()
            #Close connection
            cursor.close()
            if file.filename == '':
                flash('No selected file')
                return redirect(url_for('add_asset'))
            if file:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('asset Created', 'success')
            return redirect(url_for('dashboard'))
    return render_template('add_asset.html', form=form) 
# Edit asset
@app.route('/edit_asset/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_asset(id):
    form = InventoryForm(request.form)
    if request.method == 'POST':
        quantity = form.quantity.data
         # Create Cursor
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
  
        # Execute
        check_asset = cursor.execute("SELECT quantity FROM assets WHERE id = %s",[id])
        
        # check_asset = cursor.fetchone()
        print(check_asset)
        if check_asset >  0:    
            cursor.execute("SELECT quantity FROM assets WHERE id = %s",[id])
            mysql.connection.commit()
            qty = cursor.fetchall()
            print(qty)
            qty1 = qty[0]
            qty2 = qty1['quantity']
            print(qty2)
            new_qty = qty2 - quantity
            cursor.execute("UPDATE assets SET quantity = %s WHERE id = %s",(new_qty, id))
            # Commit to DB
            mysql.connection.commit()
            #Close connection
            cursor.close()
            flash('asset consumed', 'success')
            return redirect(url_for('dashboard'))
            
        else:
            flash("Insufficient Assets",'danger')
            return redirect(url_for('dashboard'))
    return render_template('edit_asset.html', form=form)
            
#Approve request
@app.route('/approve_request/<string:id>', methods = ['POST'])
@is_logged_in
def approve_request(id):
    # Create cursor
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  
    cursor.execute("SELECT name, email, username, password, role FROM request WHERE id = %s",[id])
    mysql.connection.commit()
    record_req = cursor.fetchall()
    print(len(record_req))
    nested_record = record_req[0]
    name = nested_record['name']
    email = nested_record['email']
    username = nested_record['username']
    password = nested_record['password']
    role = nested_record['role']
    if len(record_req) >  0 :
        cursor.execute("INSERT INTO `accounts` (name, email, username, password, role) VALUES(%s, %s, %s, %s, %s)", (name, email, username, password, role))
        cursor.execute("UPDATE request SET status = 'approved' WHERE id = %s",[id])
        mysql.connection.commit()
    mysql.connection.commit()
    #Close connection
    cursor.close()
    flash('Request Approved', 'success')
    return redirect(url_for('dashboard'))

#Reject request
@app.route('/reject_request/<string:id>', methods = ['POST'])
@is_logged_in
def reject_request(id):
    # Create cursor 
    print(id)
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("UPDATE request SET status = 'rejected' WHERE id = %s",[id])
     # Commit to DB
    mysql.connection.commit()
    #Close connection
    cursor.close()
    flash('Request Rejected', 'success')
    return redirect(url_for('dashboard'))
    
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