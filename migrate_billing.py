"""
Migration Script to Add Billing Fields, Invoice Table, and User Roles
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from models import db
from config import Config
from sqlalchemy import text


def migrate():
    """Add billing columns to projects, create invoices table, and add role to users"""

    is_sqlite = Config.USE_SQLITE

    with app.app_context():
        print("=" * 50)
        print(f"Running billing & roles migration ({'SQLite' if is_sqlite else 'MySQL'})...")
        print("=" * 50)

        # --- Project billing fields ---
        project_columns = [
            ("halo_link", "VARCHAR(500)"),
            ("billing_client", "VARCHAR(200)"),
            ("billing_for", "VARCHAR(200)"),
            ("proposal_amount", "FLOAT DEFAULT 0.0"),
            ("is_recurring", "BOOLEAN DEFAULT 0"),
            ("monthly_amount", "FLOAT DEFAULT 0.0"),
            ("project_notes", "TEXT"),
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

        # --- Invoices table ---
        if is_sqlite:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    invoice_number VARCHAR(100),
                    amount FLOAT NOT NULL DEFAULT 0.0,
                    invoice_date DATE,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            '''
        else:
            create_sql = '''
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTO_INCREMENT,
                    project_id INTEGER NOT NULL,
                    invoice_number VARCHAR(100),
                    amount FLOAT NOT NULL DEFAULT 0.0,
                    invoice_date DATE,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            '''

        try:
            db.session.execute(text(create_sql))
            db.session.commit()
            print("  + Created invoices table")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower():
                print("  = invoices table already exists")
            else:
                print(f"  ! Error creating invoices table: {e}")

        # --- User role field ---
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'admin'"))
            db.session.commit()
            print("  + Added users.role column")
        except Exception as e:
            db.session.rollback()
            if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                print("  = users.role already exists")
            else:
                print(f"  ! Error adding users.role: {e}")

        # Set existing users to 'admin' role
        try:
            db.session.execute(text("UPDATE users SET role = 'admin' WHERE role IS NULL"))
            db.session.commit()
            print("  + Set existing users to 'admin' role")
        except Exception as e:
            db.session.rollback()
            print(f"  ! Error updating user roles: {e}")

        print("\n" + "=" * 50)
        print("Migration completed!")
        print("=" * 50)
        print("\nNew features available:")
        print("  - Billing dashboard at /billing")
        print("  - Invoice tracking per project")
        print("  - User roles: admin, developer, billing")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
