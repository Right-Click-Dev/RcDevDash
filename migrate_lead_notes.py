"""
Migration Script to Add Hours and Work Date to Lead Notes
"""

from app import app
from models import db
from sqlalchemy import text

def migrate_lead_notes():
    """Add hours and work_date columns to lead_notes table"""

    with app.app_context():
        print("Migrating lead_notes table...")

        try:
            # Add hours column (default 0.0)
            db.session.execute(text('ALTER TABLE lead_notes ADD COLUMN hours FLOAT DEFAULT 0.0'))
            print("✓ Added 'hours' column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("✓ 'hours' column already exists")
            else:
                print(f"Error adding hours column: {e}")

        try:
            # Add work_date column (default to current timestamp)
            db.session.execute(text('ALTER TABLE lead_notes ADD COLUMN work_date DATETIME'))
            # Set default value for existing rows
            db.session.execute(text('UPDATE lead_notes SET work_date = created_at WHERE work_date IS NULL'))
            print("✓ Added 'work_date' column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("✓ 'work_date' column already exists")
            else:
                print(f"Error adding work_date column: {e}")

        db.session.commit()

        print("\n" + "="*50)
        print("Database migration completed!")
        print("="*50)
        print("\nLead notes now track hours and work dates!")
        print("="*50)


if __name__ == '__main__':
    migrate_lead_notes()
