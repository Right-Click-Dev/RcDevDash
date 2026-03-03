"""
Migration Script to Add is_extension Column to Phases Table
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from models import db
from sqlalchemy import text


def migrate():
    """Add is_extension column to phases table"""

    with app.app_context():
        print("=" * 50)
        print("Running phase extension migration...")
        print("=" * 50)

        try:
            db.session.execute(text('ALTER TABLE phases ADD COLUMN is_extension BOOLEAN DEFAULT 0'))
            db.session.commit()
            print("  + Added phases.is_extension")
        except Exception as e:
            db.session.rollback()
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("  = phases.is_extension already exists")
            else:
                print(f"  ! Error adding phases.is_extension: {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
