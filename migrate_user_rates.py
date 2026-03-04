"""
Migration Script to Add hourly_rate Field to Users Table
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from models import db
from sqlalchemy import text


def migrate():
    """Add hourly_rate field to users table"""

    with app.app_context():
        print("=" * 50)
        print("Running user rates migration...")
        print("=" * 50)

        try:
            db.session.execute(text('ALTER TABLE users ADD COLUMN hourly_rate FLOAT DEFAULT 0.0'))
            db.session.commit()
            print("  + Added users.hourly_rate")
        except Exception as e:
            db.session.rollback()
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("  = users.hourly_rate already exists")
            else:
                print(f"  ! Error adding users.hourly_rate: {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
