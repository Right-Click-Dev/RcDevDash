"""
Database Update Script
This script adds the new Lead tables to the existing database
"""

from app import app
from models import db

def update_database():
    """Add new tables to the database"""

    with app.app_context():
        print("Updating database with new Lead tables...")

        # Create only the new tables (won't affect existing ones)
        db.create_all()

        print("\n" + "="*50)
        print("Database update completed!")
        print("="*50)
        print("\nNew tables added:")
        print("- leads")
        print("- lead_notes")
        print("- lead_tasks")
        print("\nYou can now use the Lead feature!")
        print("="*50)


if __name__ == '__main__':
    update_database()
