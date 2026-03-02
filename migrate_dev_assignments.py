"""
Migration Script to Add Developer Project Assignments and Task Assignment
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from models import db
from config import Config
from sqlalchemy import text


def migrate():
    """Create project_assignments table and add assigned_to_id to tasks"""

    is_sqlite = Config.USE_SQLITE

    with app.app_context():
        print("=" * 50)
        print(f"Running dev assignments migration ({'SQLite' if is_sqlite else 'MySQL'})...")
        print("=" * 50)

        # --- project_assignments table ---
        if is_sqlite:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS project_assignments (
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, project_id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            '''
        else:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS project_assignments (
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, project_id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            '''

        try:
            db.session.execute(text(create_sql))
            db.session.commit()
            print("  + Created project_assignments table")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower():
                print("  = project_assignments table already exists")
            else:
                print(f"  ! Error creating project_assignments table: {e}")

        # --- Task assigned_to_id column ---
        try:
            db.session.execute(text('ALTER TABLE tasks ADD COLUMN assigned_to_id INTEGER'))
            db.session.commit()
            print("  + Added tasks.assigned_to_id column")
        except Exception as e:
            db.session.rollback()
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("  = tasks.assigned_to_id already exists")
            else:
                print(f"  ! Error adding tasks.assigned_to_id: {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)
        print("\nNew features available:")
        print("  - Admin can assign developers to projects")
        print("  - Tasks can be assigned to individual developers")
        print("  - Developers see only their assigned projects")
        print("  - Dev-focused project view at /project/<id>/dev-view")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
