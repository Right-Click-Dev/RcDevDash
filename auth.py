from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from models import db, User

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Validate input
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')

        # Find user
        user = User.query.filter_by(username=username).first()

        # Verify credentials
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Login successful!', 'success')

            # Redirect to next page or home
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('home'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
