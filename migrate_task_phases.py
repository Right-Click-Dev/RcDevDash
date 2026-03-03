"""
Migration Script: Catch-up migration for PythonAnywhere.
Ensures all tables and columns exist. Safe to run multiple times.
Works with both SQLite (local) and MySQL (PythonAnywhere).
"""

from app import app
from models import db
from config import Config
from sqlalchemy import text


def add_column(col_name, col_type, table='projects'):
    """Helper to add a column, ignoring if it already exists."""
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


def create_table(name, sql):
    """Helper to create a table, ignoring if it already exists."""
    try:
        db.session.execute(text(sql))
        db.session.commit()
        print(f"  + Ensured {name} table exists")
    except Exception as e:
        db.session.rollback()
        if "already exists" in str(e).lower():
            print(f"  = {name} table already exists")
        else:
            print(f"  ! Error creating {name} table: {e}")


def migrate():
    is_sqlite = Config.USE_SQLITE
    auto_inc = 'AUTOINCREMENT' if is_sqlite else 'AUTO_INCREMENT'
    engine_suffix = '' if is_sqlite else ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'

    with app.app_context():
        print("=" * 50)
        print(f"Running catch-up migration ({'SQLite' if is_sqlite else 'MySQL'})...")
        print("=" * 50)

        # =====================================================================
        # 1. Ensure all tables exist
        # =====================================================================

        # --- expenses table ---
        create_table('expenses', f'''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY {auto_inc},
                project_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                amount FLOAT NOT NULL DEFAULT 0.0,
                category VARCHAR(100) DEFAULT 'General',
                expense_date DATE,
                invoiced BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            ){engine_suffix}
        ''')

        # --- project_links table ---
        create_table('project_links', f'''
            CREATE TABLE IF NOT EXISTS project_links (
                id INTEGER PRIMARY KEY {auto_inc},
                project_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                url VARCHAR(500) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            ){engine_suffix}
        ''')

        # --- project_comments table ---
        create_table('project_comments', f'''
            CREATE TABLE IF NOT EXISTS project_comments (
                id INTEGER PRIMARY KEY {auto_inc},
                project_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                comment TEXT NOT NULL,
                page_type VARCHAR(20) DEFAULT 'dev',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            ){engine_suffix}
        ''')

        # --- clients table ---
        create_table('clients', f'''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY {auto_inc},
                name VARCHAR(200) NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ){engine_suffix}
        ''')

        # --- phases table ---
        create_table('phases', f'''
            CREATE TABLE IF NOT EXISTS phases (
                id INTEGER PRIMARY KEY {auto_inc},
                project_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                amount FLOAT DEFAULT 0.0,
                hours_budget FLOAT DEFAULT 0.0,
                status VARCHAR(50) DEFAULT 'not_started',
                sort_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            ){engine_suffix}
        ''')

        # --- project_assignments table ---
        create_table('project_assignments', f'''
            CREATE TABLE IF NOT EXISTS project_assignments (
                user_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, project_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            ){engine_suffix}
        ''')

        # =====================================================================
        # 2. Ensure all columns exist on projects table
        # =====================================================================
        project_columns = [
            ("client_id", "INTEGER"),
            ("start_date", "DATE"),
            ("status", "VARCHAR(20) DEFAULT 'active'"),
            ("archived_at", "DATETIME"),
            ("hourly_cost_rate", "FLOAT DEFAULT 0.0"),
            ("proposal_file_path", "VARCHAR(500)"),
            ("monthly_support_hours", "FLOAT DEFAULT 0.0"),
            ("monthly_support_amount", "FLOAT DEFAULT 0.0"),
        ]
        for col_name, col_type in project_columns:
            add_column(col_name, col_type, 'projects')

        # Set existing projects to 'active' status if null
        try:
            db.session.execute(text("UPDATE projects SET status = 'active' WHERE status IS NULL"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # =====================================================================
        # 3. Ensure all columns exist on users table
        # =====================================================================
        add_column("role", "VARCHAR(20) DEFAULT 'admin'", 'users')

        # =====================================================================
        # 4. Add phase_id to tasks table
        # =====================================================================
        add_column("phase_id", "INTEGER", 'tasks')

        # Add FK constraint (MySQL only)
        if not is_sqlite:
            try:
                db.session.execute(text(
                    'ALTER TABLE tasks ADD CONSTRAINT fk_tasks_phase_id '
                    'FOREIGN KEY (phase_id) REFERENCES phases(id)'
                ))
                db.session.commit()
                print("  + Added FK constraint tasks.phase_id -> phases.id")
            except Exception as e:
                db.session.rollback()
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    print("  = FK constraint already exists")
                else:
                    print(f"  ! FK constraint (non-critical): {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
