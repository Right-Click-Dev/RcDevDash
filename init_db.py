"""
Database Initialization Script
This script creates all database tables and initializes the admin user
"""

from app import app
from models import db, User, Project, WorkItem, Task
from datetime import datetime


def init_database():
    """Initialize the database and create admin user"""

    with app.app_context():
        print("Creating database tables...")

        # Drop all tables (use with caution!)
        # db.drop_all()

        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

        # Check if admin user already exists
        admin_user = User.query.filter_by(username='ConnerS').first()

        if not admin_user:
            print("\nCreating admin user...")
            admin_user = User(
                username='ConnerS',
                is_admin=True
            )
            admin_user.set_password('Future!2000')
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user created: {admin_user.username}")
        else:
            print(f"\nAdmin user already exists: {admin_user.username}")

        # Optional: Create sample project for testing
        sample_project = Project.query.filter_by(name='Sample Project').first()
        if not sample_project:
            print("\nCreating sample project...")
            sample_project = Project(
                name='Sample Project',
                description='This is a sample project to demonstrate the dashboard features.',
                hours_budget=100.0
            )
            db.session.add(sample_project)
            db.session.commit()

            # Add sample work items
            work_item1 = WorkItem(
                project_id=sample_project.id,
                description='Initial project setup and planning',
                hours=5.0,
                work_date=datetime.now()
            )
            work_item2 = WorkItem(
                project_id=sample_project.id,
                description='Database design and implementation',
                hours=8.0,
                work_date=datetime.now()
            )
            db.session.add(work_item1)
            db.session.add(work_item2)

            # Add sample tasks
            task1 = Task(
                project_id=sample_project.id,
                description='Complete frontend design',
                deadline=datetime(2024, 12, 31).date()
            )
            task2 = Task(
                project_id=sample_project.id,
                description='Deploy to PythonAnywhere',
                deadline=datetime(2024, 12, 15).date()
            )
            task3 = Task(
                project_id=sample_project.id,
                description='Write documentation',
                completed=True,
                completed_at=datetime.now()
            )
            db.session.add(task1)
            db.session.add(task2)
            db.session.add(task3)

            db.session.commit()
            print("Sample project created successfully!")

        print("\n" + "="*50)
        print("Database initialization completed!")
        print("="*50)
        print("\nAdmin Login Credentials:")
        print("Username: ConnerS")
        print("Password: Future!2000")
        print("\nYou can now run the application with: python app.py")
        print("="*50)


if __name__ == '__main__':
    init_database()
