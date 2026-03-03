"""
Migration Script - Add missing columns to projects and phases tables
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from models import db
from sqlalchemy import text


def migrate():
    with app.app_context():
        print("=" * 50)
        print("Running migration...")
        print("=" * 50)

        columns = [
            ("projects", "monthly_support_hours", "FLOAT DEFAULT 0"),
            ("projects", "monthly_support_amount", "FLOAT DEFAULT 0"),
            ("projects", "proposal_file_path", "VARCHAR(500)"),
            ("phases", "is_extension", "BOOLEAN DEFAULT 0"),
            ("clients", "contact_name", "VARCHAR(200)"),
            ("clients", "contact_email", "VARCHAR(200)"),
            ("clients", "contact_phone", "VARCHAR(50)"),
        ]

        for table, col_name, col_type in columns:
            try:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN {col_name} {col_type}'))
                db.session.commit()
                print(f"  + Added {table}.{col_name}")
            except Exception as e:
                db.session.rollback()
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"  = {table}.{col_name} already exists")
                else:
                    print(f"  ! Error adding {table}.{col_name}: {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
