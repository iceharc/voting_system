from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from models import User, db
from datetime import datetime
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET'])
def home():
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # --- Validation ---
        if len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('auth.register'))

        # --- Check duplicates ---
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("Username or email already exists.", "warning")
            return redirect(url_for('auth.register'))

        # --- Save user ---
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(
            username=username,
            email=email,
            phone=phone,
            password=hashed_password,
            role='user'
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            print(f"Error during registration: {e}")
            flash("An error occurred. Please try again.", "danger")
            return redirect(url_for('auth.register'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # ✅ Always clear old session and flash messages on GET
    if request.method == 'GET':
        session.clear()  # remove all previous session data
        # Note: flash messages are stored in the session, so this also clears them

    if request.method == 'POST':
        identifier = request.form['username']
        password = request.form['password']

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and check_password_hash(user.password, password):
            login_user(user)

            if user.role == 'admin':
                flash(f"Welcome back, Admin {user.username}!", "success")
                return redirect(url_for('admin.admin_dashboard'))
            else:
                flash(f"Welcome {user.username}!", "success")
                return redirect(url_for('user.user_dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('login.html',now=datetime.now)


@auth_bp.route('/logout')
def logout():
    logout_user()
    session.clear()  # ✅ also clear all session data after logout
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
