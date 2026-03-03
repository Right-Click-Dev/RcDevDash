"""
Migration Script: Add phase_id column to tasks table
Links tasks to phases so they can be grouped by phase.
Works with both SQLite (local) and MySQL (PythonAnywhere)
"""

from app import app
from models import db
from config import Config
from sqlalchemy import text


def migrate():
    """Add phase_id column to tasks table"""

    is_sqlite = Config.USE_SQLITE

    with app.app_context():
        print("=" * 50)
        print(f"Running task phases migration ({'SQLite' if is_sqlite else 'MySQL'})...")
        print("=" * 50)

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

        # --- Add foreign key constraint (MySQL only, SQLite doesn't support ADD CONSTRAINT) ---
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
        print("\nNew features available:")
        print("  - Assign tasks to phases when creating them")
        print("  - Tasks grouped by phase on project detail page")
        print("  - Current phase shown on developer project view")
        print("=" * 50)


if __name__ == '__main__':
    migrate()
