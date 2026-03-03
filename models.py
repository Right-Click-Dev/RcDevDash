from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

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


class Client(db.Model):
    """Client model for grouping projects"""
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    projects = db.relationship('Project', backref='client', lazy=True)

    def __repr__(self):
        return f'<Client {self.name}>'


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
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, on_hold, archived
    archived_at = db.Column(db.DateTime, nullable=True)
    hourly_cost_rate = db.Column(db.Float, default=0.0)
    monthly_support_hours = db.Column(db.Float, default=0.0)
    monthly_support_amount = db.Column(db.Float, default=0.0)
    proposal_file_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    work_items = db.relationship('WorkItem', backref='project', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='project', lazy=True, cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='project', lazy=True, cascade='all, delete-orphan')
    phases = db.relationship('Phase', backref='project', lazy=True, cascade='all, delete-orphan', order_by='Phase.sort_order')
    comments = db.relationship('ProjectComment', backref='project', lazy=True, cascade='all, delete-orphan')
    links = db.relationship('ProjectLink', backref='project', lazy=True, cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='project', lazy=True, cascade='all, delete-orphan')

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
    def monthly_support_months(self):
        """Count how many 1st-of-month dates have passed since the start date"""
        if not self.start_date or (self.monthly_support_hours == 0 and self.monthly_support_amount == 0):
            return 0
        today = date.today()
        start = self.start_date
        if start > today:
            return 0
        # Count months from start_date through today where the 1st has passed
        months = (today.year - start.year) * 12 + (today.month - start.month)
        # If start day is after the 1st, the first month's 1st hadn't occurred yet at start
        if start.day > 1:
            months = max(months, 0)
        else:
            months += 1  # Include the starting month since start is on or before the 1st
        return max(months, 0)

    @property
    def monthly_support_hours_accrued(self):
        """Total support hours accrued"""
        return self.monthly_support_hours * self.monthly_support_months

    @property
    def monthly_support_amount_accrued(self):
        """Total support $ accrued"""
        return self.monthly_support_amount * self.monthly_support_months

    @property
    def remaining_balance(self):
        """Calculate remaining balance including uninvoiced expenses and monthly support"""
        return self.proposal_amount + self.total_uninvoiced_expenses + self.monthly_support_amount_accrued - self.total_invoiced

    @property
    def billing_display(self):
        """Display string for billing relationship"""
        if self.billing_client and self.billing_for:
            return f"{self.billing_client} for {self.billing_for}"
        return self.billing_client or self.billing_for or ''

    @property
    def total_phase_amount(self):
        """Calculate total amount across all phases"""
        return sum(p.amount for p in self.phases)

    @property
    def is_archived(self):
        """Check if project is archived"""
        return self.status == 'archived'

    @property
    def is_on_hold(self):
        """Check if project is on hold"""
        return self.status == 'on_hold'

    @property
    def total_expenses(self):
        """Calculate total expenses"""
        return sum(e.amount for e in self.expenses)

    @property
    def total_uninvoiced_expenses(self):
        """Calculate total uninvoiced expenses"""
        return sum(e.amount for e in self.expenses if not e.invoiced)

    @property
    def dev_cost(self):
        """Calculate development cost based on hours and cost rate"""
        return self.hours_used * self.hourly_cost_rate

    @property
    def total_cost(self):
        """Calculate total cost (dev cost + expenses)"""
        return self.dev_cost + self.total_expenses

    @property
    def profit(self):
        """Calculate profit (revenue - dev cost - expenses)"""
        return self.proposal_amount - self.dev_cost - self.total_expenses

    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.proposal_amount == 0:
            return 0
        return (self.profit / self.proposal_amount) * 100

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
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    created_by = db.relationship('User', backref='work_items_created', foreign_keys=[created_by_id])

    def __repr__(self):
        return f'<WorkItem {self.id}: {self.hours}hrs>'


class Task(db.Model):
    """Task model for project task lists"""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    phase_id = db.Column(db.Integer, db.ForeignKey('phases.id'), nullable=True)
    description = db.Column(db.Text, nullable=False)
    deadline = db.Column(db.Date, nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assigned_to = db.relationship('User', backref='assigned_tasks', foreign_keys=[assigned_to_id])
    phase = db.relationship('Phase', backref='tasks')

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


class Phase(db.Model):
    """Phase model for project milestones linked to billing"""
    __tablename__ = 'phases'

    STATUSES = ['not_started', 'in_progress', 'completed', 'invoiced']

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(db.Float, default=0.0)
    hours_budget = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default='not_started')
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def status_display(self):
        """Human-readable status"""
        return self.status.replace('_', ' ').title()

    @property
    def next_status(self):
        """Get next status in progression"""
        idx = self.STATUSES.index(self.status)
        if idx < len(self.STATUSES) - 1:
            return self.STATUSES[idx + 1]
        return None

    def __repr__(self):
        return f'<Phase {self.name}>'


class ProjectComment(db.Model):
    """Comments for project pages (dev or billing)"""
    __tablename__ = 'project_comments'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    page_type = db.Column(db.String(20), default='dev')  # 'dev' or 'billing'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='comments')

    def __repr__(self):
        return f'<ProjectComment {self.id}>'


class Expense(db.Model):
    """Expense model for tracking project costs to invoice against"""
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    category = db.Column(db.String(100), default='General')
    expense_date = db.Column(db.Date, default=datetime.utcnow)
    invoiced = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Expense {self.id}: ${self.amount:.2f}>'


class ProjectLink(db.Model):
    """Links associated with a project (shown on billing page)"""
    __tablename__ = 'project_links'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ProjectLink {self.title}>'
