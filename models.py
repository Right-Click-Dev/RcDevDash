from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# Association table for many-to-many User <-> Project assignments
project_assignments = db.Table('project_assignments',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('projects.id'), primary_key=True),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow)
)


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'

    # Role constants
    ROLE_ADMIN = 'admin'
    ROLE_DEVELOPER = 'developer'
    ROLE_BILLING = 'billing'
    ROLES = [ROLE_ADMIN, ROLE_DEVELOPER, ROLE_BILLING]

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=True)
    role = db.Column(db.String(20), default=ROLE_ADMIN)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assigned_projects = db.relationship('Project', secondary=project_assignments, backref=db.backref('assigned_developers', lazy=True), lazy=True)

    @property
    def can_access_dev(self):
        """Check if user can access developer pages"""
        return self.role in (self.ROLE_ADMIN, self.ROLE_DEVELOPER)

    @property
    def can_access_billing(self):
        """Check if user can access billing pages"""
        return self.role in (self.ROLE_ADMIN, self.ROLE_BILLING)

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
    halo_link = db.Column(db.String(500))
    billing_client = db.Column(db.String(200))  # Who's paying (e.g., "ESRI")
    billing_for = db.Column(db.String(200))  # Who the work is for (e.g., "TCG")
    proposal_amount = db.Column(db.Float, default=0.0)
    is_recurring = db.Column(db.Boolean, default=False)
    monthly_amount = db.Column(db.Float, default=0.0)
    project_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    work_items = db.relationship('WorkItem', backref='project', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='project', lazy=True, cascade='all, delete-orphan')

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

    @property
    def total_invoiced(self):
        """Calculate total amount invoiced"""
        return sum(inv.amount for inv in self.invoices)

    @property
    def remaining_balance(self):
        """Calculate remaining balance from proposal"""
        return self.proposal_amount - self.total_invoiced

    @property
    def billing_display(self):
        """Display string for billing relationship"""
        if self.billing_client and self.billing_for:
            return f"{self.billing_client} for {self.billing_for}"
        return self.billing_client or self.billing_for or ''

    def tasks_for_user(self, user_id):
        """Return tasks assigned to a specific user"""
        return [t for t in self.tasks if t.assigned_to_id == user_id]

    def task_count_for_user(self, user_id):
        """Return count of tasks assigned to a specific user"""
        return len(self.tasks_for_user(user_id))

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
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assigned_to = db.relationship('User', backref='assigned_tasks', foreign_keys=[assigned_to_id])

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


class Invoice(db.Model):
    """Invoice model for tracking billing against projects"""
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    invoice_number = db.Column(db.String(100))
    amount = db.Column(db.Float, nullable=False, default=0.0)
    invoice_date = db.Column(db.Date, default=datetime.utcnow)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Invoice {self.invoice_number}: ${self.amount:.2f}>'


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
