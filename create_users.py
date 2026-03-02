"""
Script to create users for the RcDevDash application.
Run this in PythonAnywhere's Bash console after uploading to your project directory.

Usage:
    python create_users.py
"""
from app import app, db
from models import User


def create_user(username, password, is_admin=True):
    """Create a new user"""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"User '{username}' already exists!")
            return False

        # Create new user
        user = User(username=username, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        print(f"User '{username}' created successfully!")
        return True


def main():
    """Create initial users"""
    print("Creating users for RcDevDash...")
    print("-" * 50)

    # Create admin user(s)
    # IMPORTANT: Change these credentials!
    users_to_create = [
        ("admin", "your_secure_password_here", True),
        # Add more users as needed:
        # ("username2", "password2", True),
    ]

    for username, password, is_admin in users_to_create:
        create_user(username, password, is_admin)

    print("-" * 50)
    print("Done!")


if __name__ == '__main__':
    main()
