"""
Migration Script: Ensure expenses table exists + add phase_id column to tasks table.
Works with both SQLite (local) and MySQL (PythonAnywhere).
Safe to run multiple times.
"""

from app import app
from models import db
from config import Config
from sqlalchemy import text


def migrate():
    """Create missing tables and add phase_id to tasks"""

    is_sqlite = Config.USE_SQLITE

    with app.app_context():
        print("=" * 50)
        print(f"Running migration ({'SQLite' if is_sqlite else 'MySQL'})...")
        print("=" * 50)

        # --- Ensure expenses table exists ---
        if is_sqlite:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    amount FLOAT NOT NULL DEFAULT 0.0,
                    category VARCHAR(100) DEFAULT 'General',
                    expense_date DATE DEFAULT CURRENT_DATE,
                    invoiced BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            '''
        else:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    project_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    amount FLOAT NOT NULL DEFAULT 0.0,
                    category VARCHAR(100) DEFAULT 'General',
                    expense_date DATE DEFAULT (CURRENT_DATE),
                    invoiced BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            '''

        try:
            db.session.execute(text(create_sql))
            db.session.commit()
            print("  + Ensured expenses table exists")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower():
                print("  = expenses table already exists")
            else:
                print(f"  ! Error creating expenses table: {e}")

        # --- Add phase_id column to tasks table ---
        try:
            db.session.execute(text('ALTER TABLE tasks ADD COLUMN phase_id INTEGER'))
            db.session.commit()
            print("  + Added tasks.phase_id column")
        except Exception as e:
            db.session.rollback()
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("  = tasks.phase_id already exists")
            else:
                print(f"  ! Error adding tasks.phase_id: {e}")

        # --- Add foreign key constraint (MySQL only) ---
        if not is_sqlite:
            try:
                db.session.execute(text(
                    'ALTER TABLE tasks ADD CONSTRAINT fk_tasks_phase_id '
                    'FOREIGN KEY (phase_id) REFERENCES phases(id)'
                ))
                db.session.commit()
                print("  + Added foreign key constraint for tasks.phase_id")
            except Exception as e:
                db.session.rollback()
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    print("  = Foreign key constraint already exists")
                else:
                    print(f"  ! Error adding foreign key (non-critical): {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
