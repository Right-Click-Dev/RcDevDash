"""
Migration Script for Customer Role, Customer Assignments & Customer Requests
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from config import Config
from models import db
from sqlalchemy import text


def migrate():
    """Add customer-related columns and tables"""

    with app.app_context():
        print("=" * 60)
        print("Running customer feature migration...")
        print("=" * 60)

        # --- Column additions ---
        columns = [
            ("users", "client_id", "ALTER TABLE users ADD COLUMN client_id INTEGER"),
            ("users", "hourly_rate", "ALTER TABLE users ADD COLUMN hourly_rate FLOAT DEFAULT 0.0"),
            ("tasks", "is_support", "ALTER TABLE tasks ADD COLUMN is_support BOOLEAN DEFAULT 0"),
            ("work_items", "is_support", "ALTER TABLE work_items ADD COLUMN is_support BOOLEAN DEFAULT 0"),
        ]

        print("\n-- Column migrations --")
        for table, col, sql in columns:
            try:
                db.session.execute(text(sql))
                db.session.commit()
                print(f"  + Added {table}.{col}")
            except Exception as e:
                db.session.rollback()
                msg = str(e).lower()
                if "duplicate" in msg or "already exists" in msg:
                    print(f"  = {table}.{col} already exists")
                else:
                    print(f"  ! Error adding {table}.{col}: {e}")

        # --- Table creation ---
        is_sqlite = Config.USE_SQLITE
        print(f"\n-- Table migrations ({'SQLite' if is_sqlite else 'MySQL'}) --")

        if is_sqlite:
            tables = {
                'poc_assignments': '''CREATE TABLE IF NOT EXISTS poc_assignments (
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, project_id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )''',
                'customer_assignments': '''CREATE TABLE IF NOT EXISTS customer_assignments (
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, project_id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )''',
                'customer_requests': '''CREATE TABLE IF NOT EXISTS customer_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    submitted_by_id INTEGER NOT NULL,
                    request_type VARCHAR(50) NOT NULL,
                    title VARCHAR(300) NOT NULL,
                    description TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'open',
                    admin_notes TEXT,
                    converted_task_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (submitted_by_id) REFERENCES users(id),
                    FOREIGN KEY (converted_task_id) REFERENCES tasks(id)
                )''',
            }
        else:
            tables = {
                'poc_assignments': '''CREATE TABLE IF NOT EXISTS poc_assignments (
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, project_id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
                'customer_assignments': '''CREATE TABLE IF NOT EXISTS customer_assignments (
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, project_id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
                'customer_requests': '''CREATE TABLE IF NOT EXISTS customer_requests (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    project_id INTEGER NOT NULL,
                    submitted_by_id INTEGER NOT NULL,
                    request_type VARCHAR(50) NOT NULL,
                    title VARCHAR(300) NOT NULL,
                    description TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'open',
                    admin_notes TEXT,
                    converted_task_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (submitted_by_id) REFERENCES users(id),
                    FOREIGN KEY (converted_task_id) REFERENCES tasks(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''',
            }

        for name, sql in tables.items():
            try:
                db.session.execute(text(sql))
                db.session.commit()
                print(f"  + Created/verified table: {name}")
            except Exception as e:
                db.session.rollback()
                print(f"  ! Error creating {name}: {e}")

        print("\n" + "=" * 60)
        print("Migration completed!")
        print("=" * 60)


if __name__ == '__main__':
    migrate()
