"""
Migration Script to Add created_by_id to WorkItem
Tracks which user created each work item so developers can edit their own submissions.
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from models import db
from config import Config
from sqlalchemy import text


def migrate():
    """Add created_by_id column to work_items table"""

    with app.app_context():
        print("=" * 50)
        print(f"Running work item creator migration ({'SQLite' if Config.USE_SQLITE else 'MySQL'})...")
        print("=" * 50)

        try:
            db.session.execute(text('ALTER TABLE work_items ADD COLUMN created_by_id INTEGER'))
            db.session.commit()
            print("  + Added work_items.created_by_id column")
        except Exception as e:
            db.session.rollback()
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("  = work_items.created_by_id already exists")
            else:
                print(f"  ! Error adding work_items.created_by_id: {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)
        print("\nNew features available:")
        print("  - Developers can edit their own tasks from the dev view")
        print("  - Developers can edit work entries they submitted")
        print("  - 'My Work Entries' section in the dev project view")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
