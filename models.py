from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify the user's password"""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Project(db.Model):
    """Project model"""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    hours_budget = db.Column(db.Float, default=0.0)
    project_type = db.Column(db.String(50), default='External')  # External or Internal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    work_items = db.relationship('WorkItem', backref='project', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')

    @property
    def hours_used(self):
        """Calculate total hours used from work items"""
        return sum(item.hours for item in self.work_items)

    @property
    def hours_remaining(self):
        """Calculate remaining hours"""
        return self.hours_budget - self.hours_used

    @property
    def is_over_budget(self):
        """Check if project is over budget"""
        return self.hours_used > self.hours_budget

    @property
    def progress_percentage(self):
        """Calculate progress as percentage"""
        if self.hours_budget == 0:
            return 0
        percentage = (self.hours_used / self.hours_budget) * 100
        return min(percentage, 100)  # Cap at 100%

    def __repr__(self):
        return f'<Project {self.name}>'


class WorkItem(db.Model):
    """Work item model for tracking time entries"""
    __tablename__ = 'work_items'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    work_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WorkItem {self.id}: {self.hours}hrs>'


class Task(db.Model):
    """Task model for project task lists"""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def toggle_completed(self):
        """Toggle task completion status"""
        self.completed = not self.completed
        self.completed_at = datetime.utcnow() if self.completed else None

    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if not self.deadline or self.completed:
            return False
        return datetime.now().date() > self.deadline

    def __repr__(self):
        return f'<Task {self.id}: {self.description[:30]}>'


class Lead(db.Model):
    """Lead model for potential projects"""
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    estimated_hours = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='New')  # New, Contacted, Qualified, Lost
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    notes = db.relationship('LeadNote', backref='lead', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('LeadTask', backref='lead', lazy=True, cascade='all, delete-orphan')

    @property
    def hours_logged(self):
        """Calculate total hours logged from notes"""
        return sum(note.hours for note in self.notes)

    def __repr__(self):
        return f'<Lead {self.name}>'


class LeadNote(db.Model):
    """Notes for leads"""
    __tablename__ = 'lead_notes'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    note = db.Column(db.Text, nullable=False)
    hours = db.Column(db.Float, default=0.0)
    work_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<LeadNote {self.id}>'


class LeadTask(db.Model):
    """Tasks for leads"""
    __tablename__ = 'lead_tasks'

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def toggle_completed(self):
        """Toggle task completion status"""
        self.completed = not self.completed
        self.completed_at = datetime.utcnow() if self.completed else None

    @property
    def is_overdue(self):
        """Check if task is overdue"""
        if not self.deadline or self.completed:
            return False
        return datetime.now().date() > self.deadline

    def __repr__(self):
        return f'<LeadTask {self.id}: {self.description[:30]}>'
