#!/usr/bin/env python3
"""
Quick user creation script for PythonAnywhere.
This script can be run from anywhere in your PythonAnywhere environment.

Usage:
    1. Upload this file to PythonAnywhere
    2. Navigate to your project directory (where app.py is located)
    3. Run: python3 quick_create_user.py

Or if you're not sure where your project is:
    1. Find your project: find ~ -name "app.py" -type f
    2. cd to that directory
    3. Run: python3 quick_create_user.py
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app import app, db
    from models import User

    def create_user_interactive():
        """Create a user with interactive prompts"""
        print("\n=== RcDevDash User Creation ===\n")

        username = input("Enter username: ").strip()
        if not username:
            print("Username cannot be empty!")
            return

        password = input("Enter password: ").strip()
        if not password:
            print("Password cannot be empty!")
            return

        password_confirm = input("Confirm password: ").strip()
        if password != password_confirm:
            print("Passwords do not match!")
            return

        # Create user in app context
        with app.app_context():
            # Check if user already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                print(f"\nError: User '{username}' already exists!")
                return

            # Create new user
            user = User(username=username, is_admin=True)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            print(f"\n✓ User '{username}' created successfully!")
            print(f"  - Admin privileges: Yes")
            print(f"\nYou can now log in with these credentials.\n")

    if __name__ == '__main__':
        create_user_interactive()

except ImportError as e:
    print(f"\nError: Could not import required modules.")
    print(f"Details: {e}")
    print("\nMake sure you are running this script from your project directory")
    print("(the directory containing app.py, models.py, etc.)")
    print("\nTo find your project directory, run:")
    print("  find ~ -name 'app.py' -type f")
    sys.exit(1)
except Exception as e:
    print(f"\nUnexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
