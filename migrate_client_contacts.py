"""
Migration Script to Add Contact Fields to Clients Table
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from models import db
from config import Config
from sqlalchemy import text


def migrate():
    """Add contact fields to clients table"""

    with app.app_context():
        print("=" * 50)
        print("Running client contacts migration...")
        print("=" * 50)

        columns = [
            ("contact_name", "VARCHAR(200)"),
            ("contact_email", "VARCHAR(200)"),
            ("contact_phone", "VARCHAR(50)"),
        ]

        for col_name, col_type in columns:
            try:
                db.session.execute(text(f'ALTER TABLE clients ADD COLUMN {col_name} {col_type}'))
                db.session.commit()
                print(f"  + Added clients.{col_name}")
            except Exception as e:
                db.session.rollback()
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"  = clients.{col_name} already exists")
                else:
                    print(f"  ! Error adding clients.{col_name}: {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
