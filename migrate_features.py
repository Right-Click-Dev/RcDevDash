"""
Migration Script: Add Clients, Phases, Comments, Links, and Project enhancements
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from models import db
from config import Config
from sqlalchemy import text


def migrate():
    """Add new tables and columns for feature expansion"""

    is_sqlite = Config.USE_SQLITE

    with app.app_context():
        print("=" * 50)
        print(f"Running features migration ({'SQLite' if is_sqlite else 'MySQL'})...")
        print("=" * 50)

        # --- Clients table ---
        if is_sqlite:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(200) NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            '''
        else:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS clients (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    name VARCHAR(200) NOT NULL UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            '''

        try:
            db.session.execute(text(create_sql))
            db.session.commit()
            print("  + Created clients table")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower():
                print("  = clients table already exists")
            else:
                print(f"  ! Error creating clients table: {e}")

        # --- Phases table ---
        if is_sqlite:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS phases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    amount FLOAT DEFAULT 0.0,
                    hours_budget FLOAT DEFAULT 0.0,
                    status VARCHAR(50) DEFAULT 'not_started',
                    sort_order INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            '''
        else:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS phases (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    project_id INTEGER NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    amount FLOAT DEFAULT 0.0,
                    hours_budget FLOAT DEFAULT 0.0,
                    status VARCHAR(50) DEFAULT 'not_started',
                    sort_order INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            '''

        try:
            db.session.execute(text(create_sql))
            db.session.commit()
            print("  + Created phases table")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower():
                print("  = phases table already exists")
            else:
                print(f"  ! Error creating phases table: {e}")

        # --- Project Comments table ---
        if is_sqlite:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS project_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    comment TEXT NOT NULL,
                    page_type VARCHAR(20) DEFAULT 'dev',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            '''
        else:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS project_comments (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    project_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    comment TEXT NOT NULL,
                    page_type VARCHAR(20) DEFAULT 'dev',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            '''

        try:
            db.session.execute(text(create_sql))
            db.session.commit()
            print("  + Created project_comments table")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower():
                print("  = project_comments table already exists")
            else:
                print(f"  ! Error creating project_comments table: {e}")

        # --- Project Links table ---
        if is_sqlite:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS project_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    url VARCHAR(500) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            '''
        else:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS project_links (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    project_id INTEGER NOT NULL,
                    title VARCHAR(200) NOT NULL,
                    url VARCHAR(500) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            '''

        try:
            db.session.execute(text(create_sql))
            db.session.commit()
            print("  + Created project_links table")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower():
                print("  = project_links table already exists")
            else:
                print(f"  ! Error creating project_links table: {e}")

        # --- Expenses table ---
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
            print("  + Created expenses table")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower():
                print("  = expenses table already exists")
            else:
                print(f"  ! Error creating expenses table: {e}")

        # --- New columns on projects table ---
        project_columns = [
            ("client_id", "INTEGER"),
            ("start_date", "DATE"),
            ("status", "VARCHAR(20) DEFAULT 'active'"),
            ("archived_at", "DATETIME"),
            ("hourly_cost_rate", "FLOAT DEFAULT 0.0"),
            ("proposal_file_path", "VARCHAR(500)"),
        ]

        for col_name, col_type in project_columns:
            try:
                db.session.execute(text(f'ALTER TABLE projects ADD COLUMN {col_name} {col_type}'))
                db.session.commit()
                print(f"  + Added projects.{col_name}")
            except Exception as e:
                db.session.rollback()
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"  = projects.{col_name} already exists")
                else:
                    print(f"  ! Error adding projects.{col_name}: {e}")

        # Set existing projects to 'active' status
        try:
            db.session.execute(text("UPDATE projects SET status = 'active' WHERE status IS NULL"))
            db.session.commit()
            print("  + Set existing projects to 'active' status")
        except Exception as e:
            db.session.rollback()
            print(f"  ! Error updating project statuses: {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)
        print("\nNew features available:")
        print("  - Client management and project grouping")
        print("  - Project phases with billing milestones")
        print("  - Comments on dev and billing pages")
        print("  - Project links on billing page")
        print("  - Project archiving")
        print("  - Profitability calculator")
        print("  - Expense tracking")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
