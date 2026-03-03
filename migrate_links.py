"""
Migration Script to Add Link Fields to Expenses and Phases Tables
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from models import db
from sqlalchemy import text


def migrate():
    """Add link fields to expenses and phases tables"""

    with app.app_context():
        print("=" * 50)
        print("Running links migration...")
        print("=" * 50)

        # Create expenses table if it doesn't exist
        tables_to_alter = [
            ("expenses", "link", "VARCHAR(500)"),
            ("phases", "link", "VARCHAR(500)"),
        ]

        for table_name, col_name, col_type in tables_to_alter:
            try:
                db.session.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}'))
                db.session.commit()
                print(f"  + Added {table_name}.{col_name}")
            except Exception as e:
                db.session.rollback()
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"  = {table_name}.{col_name} already exists")
                else:
                    print(f"  ! Error adding {table_name}.{col_name}: {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
