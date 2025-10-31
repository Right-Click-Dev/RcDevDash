"""
Migration Script to Add Project Type to Projects
"""

from app import app
from models import db
from sqlalchemy import text

def migrate_project_type():
    """Add project_type column to projects table"""

    with app.app_context():
        print("Migrating projects table...")

        try:
            # Add project_type column (default 'External')
            db.session.execute(text("ALTER TABLE projects ADD COLUMN project_type VARCHAR(50) DEFAULT 'External'"))
            # Set default value for existing rows
            db.session.execute(text("UPDATE projects SET project_type = 'External' WHERE project_type IS NULL"))
            print("Added 'project_type' column")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("'project_type' column already exists")
            else:
                print(f"Error adding project_type column: {e}")

        db.session.commit()

        print("\n" + "="*50)
        print("Database migration completed!")
        print("="*50)
        print("\nProjects now have Internal/External categorization!")
        print("All existing projects set to 'External' by default.")
        print("="*50)


if __name__ == '__main__':
    migrate_project_type()
