from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from models import User

auth = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        username = data.get('username')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        try:
            # Hash the password before storing
            hashed_password = generate_password_hash(password)
            user = User.create(email=email, password=hashed_password, username=username)
            session['user_id'] = user.id
            return jsonify({'message': 'Registration successful', 'redirect': url_for('index')}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 400

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            # Create default books for the user
            from app import get_default_books
            get_default_books(user.id)
            return jsonify({'message': 'Login successful'}), 200
        
        return jsonify({'error': 'Invalid email or password'}), 401

@auth.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logout successful', 'redirect': url_for('login')}), 200 