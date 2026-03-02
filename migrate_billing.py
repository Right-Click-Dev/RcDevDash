"""
Migration Script to Add Billing Fields, Invoice Table, and User Roles
"""

from app import app
from models import db
from sqlalchemy import text


def migrate():
    """Add billing columns to projects, create invoices table, and add role to users"""

    with app.app_context():
        print("=" * 50)
        print("Running billing & roles migration...")
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
                print(f"  + Added projects.{col_name}")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"  = projects.{col_name} already exists")
                else:
                    print(f"  ! Error adding projects.{col_name}: {e}")

        db.session.commit()

        # --- Invoices table ---
        try:
            db.session.execute(text('''
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
            '''))
            print("  + Created invoices table")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("  = invoices table already exists")
            else:
                print(f"  ! Error creating invoices table: {e}")

        db.session.commit()

        # --- User role field ---
        try:
            db.session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'admin'"))
            print("  + Added users.role column")
            # Set existing users to 'admin' role (they were all admins before)
            db.session.execute(text("UPDATE users SET role = 'admin' WHERE role IS NULL"))
            print("  + Set existing users to 'admin' role")
        except Exception as e:
            if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                print("  = users.role already exists")
            else:
                print(f"  ! Error adding users.role: {e}")

        db.session.commit()

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
