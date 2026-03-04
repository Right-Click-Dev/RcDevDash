import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import LoginManager, login_required, current_user
from datetime import datetime, date
from config import Config
from models import (db, User, Project, WorkItem, Task, Lead, LeadNote, LeadTask, Invoice,
                    Client, Phase, ProjectComment, ProjectLink, Expense, project_assignments)
from auth import auth_bp
from reports import generate_project_report

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'

# Register blueprints
app.register_blueprint(auth_bp)


@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return User.query.get(int(user_id))


# =============================================================================
# ACCESS CONTROL DECORATORS
# =============================================================================

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def billing_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.can_access_billing:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def dev_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.can_access_dev:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# AUTO-CREATE MONTHLY SUPPORT PHASES
# =============================================================================

_support_phases_checked = None


def ensure_monthly_support_phases():
    """Auto-create current month's support phase for projects with support hours/amount."""
    today = date.today()
    month_name = today.strftime('%B %Y')  # e.g., "March 2026"

    projects = Project.query.filter(
        Project.status != 'archived',
        db.or_(Project.monthly_support_hours > 0, Project.monthly_support_amount > 0)
    ).all()

    for project in projects:
        if not project.start_date or project.start_date > today:
            continue

        phase_name = f"{month_name} Support Hours"

        existing = Phase.query.filter_by(
            project_id=project.id,
            name=phase_name
        ).first()

        if not existing:
            max_order = db.session.query(db.func.max(Phase.sort_order)).filter_by(
                project_id=project.id
            ).scalar() or 0
            phase = Phase(
                project_id=project.id,
                name=phase_name,
                amount=project.monthly_support_amount,
                hours_budget=project.monthly_support_hours,
                sort_order=max_order + 1,
                status='in_progress'
            )
            db.session.add(phase)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.before_request
def check_support_phases():
    """Run support phase check once per day."""
    global _support_phases_checked
    today = date.today()
    if _support_phases_checked == today:
        return
    _support_phases_checked = today
    try:
        ensure_monthly_support_phases()
    except Exception:
        pass


@app.route('/')
@login_required
def home():
    """Home page - display all projects and leads"""
    # Billing-only users get redirected to billing dashboard
    if not current_user.can_access_dev:
        return redirect(url_for('billing_dashboard'))

    show_archived = request.args.get('show_archived', '0') == '1'
    clients = Client.query.order_by(Client.name).all()

    # Developers only see projects they're assigned to
    if current_user.role == User.ROLE_DEVELOPER:
        assigned = current_user.assigned_projects
        if not show_archived:
            assigned = [p for p in assigned if p.status != 'archived']
        external_projects = [p for p in assigned if p.project_type == 'External']
        internal_projects = [p for p in assigned if p.project_type == 'Internal']
        leads = []  # Developers don't manage leads
    else:
        base_query = Project.query
        if not show_archived:
            base_query = base_query.filter(Project.status != 'archived')
        external_projects = base_query.filter_by(project_type='External').order_by(Project.updated_at.desc()).all()
        internal_projects = base_query.filter_by(project_type='Internal').order_by(Project.updated_at.desc()).all()
        leads = Lead.query.order_by(Lead.updated_at.desc()).all()

    return render_template('home.html', external_projects=external_projects, internal_projects=internal_projects,
                           leads=leads, clients=clients, show_archived=show_archived)


@app.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    """Project detail page"""
    project = Project.query.get_or_404(project_id)

    # Developers go to their focused view
    if current_user.role == User.ROLE_DEVELOPER:
        return redirect(url_for('dev_project_view', project_id=project_id))

    work_items = WorkItem.query.filter_by(project_id=project_id).order_by(WorkItem.work_date.desc()).all()
    tasks = Task.query.filter_by(project_id=project_id).order_by(Task.completed, Task.deadline).all()
    developers = User.query.filter(User.role.in_([User.ROLE_DEVELOPER, User.ROLE_ADMIN])).order_by(User.username).all()
    dev_comments = ProjectComment.query.filter_by(project_id=project_id, page_type='dev').order_by(ProjectComment.created_at.desc()).all()
    phases = Phase.query.filter_by(project_id=project_id).order_by(Phase.sort_order).all()
    clients = Client.query.order_by(Client.name).all()
    return render_template('project_detail.html', project=project, work_items=work_items, tasks=tasks,
                           developers=developers, comments=dev_comments, phases=phases, clients=clients, now=datetime.now())


@app.route('/api/project/create', methods=['POST'])
@login_required
def create_project():
    """Create a new project"""
    try:
        name = request.form.get('name')
        description = request.form.get('description', '')
        hours_budget = float(request.form.get('hours_budget', 0))
        project_type = request.form.get('project_type', 'External')
        halo_link = request.form.get('halo_link', '').strip()
        billing_client = request.form.get('billing_client', '').strip()
        billing_for = request.form.get('billing_for', '').strip()
        proposal_amount = float(request.form.get('proposal_amount', 0) or 0)
        is_recurring = request.form.get('is_recurring') == 'on'
        monthly_amount = float(request.form.get('monthly_amount', 0) or 0)
        start_date_str = request.form.get('start_date')
        client_id = request.form.get('client_id')
        new_client_name = request.form.get('new_client_name', '').strip()

        if not name:
            flash('Project name is required.', 'error')
            return redirect(url_for('home'))

        # Handle client selection or creation
        resolved_client_id = None
        if new_client_name:
            existing = Client.query.filter_by(name=new_client_name).first()
            if existing:
                resolved_client_id = existing.id
            else:
                new_client = Client(name=new_client_name)
                db.session.add(new_client)
                db.session.flush()
                resolved_client_id = new_client.id
        elif client_id and client_id != 'new' and client_id != '':
            resolved_client_id = int(client_id)

        # Parse start date
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None

        project = Project(
            name=name,
            description=description,
            hours_budget=hours_budget,
            project_type=project_type,
            halo_link=halo_link or None,
            billing_client=billing_client or None,
            billing_for=billing_for or None,
            proposal_amount=proposal_amount,
            is_recurring=is_recurring,
            monthly_amount=monthly_amount,
            client_id=resolved_client_id,
            start_date=start_date,
            status='active'
        )
        db.session.add(project)
        db.session.commit()

        # Handle proposal file upload
        if 'proposal_file' in request.files:
            file = request.files['proposal_file']
            if file and file.filename and allowed_file(file.filename):
                from werkzeug.utils import secure_filename
                filename = secure_filename(f"project_{project.id}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                project.proposal_file_path = filename
                db.session.commit()

        flash(f'Project "{name}" created successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating project: {str(e)}', 'error')
        return redirect(url_for('home'))


@app.route('/api/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    """Delete a project"""
    try:
        project = Project.query.get_or_404(project_id)
        project_name = project.name
        db.session.delete(project)
        db.session.commit()
        flash(f'Project "{project_name}" deleted successfully.', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting project: {str(e)}', 'error')
        return redirect(url_for('home'))


@app.route('/api/workitem/add', methods=['POST'])
@login_required
def add_work_item():
    """Add a work item to a project"""
    try:
        project_id = int(request.form.get('project_id'))
        description = request.form.get('description')
        hours = float(request.form.get('hours', 0))
        work_date_str = request.form.get('work_date')

        if not description or hours <= 0:
            flash('Description and valid hours are required.', 'error')
            return redirect(url_for('project_detail', project_id=project_id))

        # Parse work date
        work_date = datetime.strptime(work_date_str, '%Y-%m-%d') if work_date_str else datetime.utcnow()

        work_item = WorkItem(
            project_id=project_id,
            description=description,
            hours=hours,
            work_date=work_date
        )
        db.session.add(work_item)
        db.session.commit()

        flash('Work item added successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding work item: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))


@app.route('/api/workitem/<int:workitem_id>/edit', methods=['POST'])
@admin_required
def edit_work_item(workitem_id):
    """Edit a work item (admin only)"""
    try:
        work_item = WorkItem.query.get_or_404(workitem_id)
        project_id = work_item.project_id

        description = request.form.get('description')
        hours = float(request.form.get('hours', 0))
        work_date_str = request.form.get('work_date')

        if not description or hours <= 0:
            flash('Description and valid hours are required.', 'error')
            return redirect(url_for('project_detail', project_id=project_id))

        # Update work item
        work_item.description = description
        work_item.hours = hours
        if work_date_str:
            work_item.work_date = datetime.strptime(work_date_str, '%Y-%m-%d')

        db.session.commit()
        flash('Work item updated successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating work item: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))


@app.route('/api/workitem/<int:workitem_id>/dev-edit', methods=['POST'])
@login_required
def dev_edit_work_item(workitem_id):
    """Edit a work item (owner only - for developers editing their own submissions)"""
    try:
        work_item = WorkItem.query.get_or_404(workitem_id)
        project_id = work_item.project_id

        # Only the creator can edit their own work items
        if work_item.created_by_id != current_user.id:
            abort(403)

        description = request.form.get('description')
        hours = float(request.form.get('hours', 0))

        if not description or hours <= 0:
            flash('Description and valid hours are required.', 'error')
            return redirect(url_for('dev_project_view', project_id=project_id))

        work_item.description = description
        work_item.hours = hours

        db.session.commit()
        flash('Work entry updated successfully!', 'success')
        return redirect(url_for('dev_project_view', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating work entry: {str(e)}', 'error')
        return redirect(url_for('dev_project_view', project_id=project_id))


@app.route('/api/workitem/<int:workitem_id>/delete', methods=['POST'])
@admin_required
def delete_work_item(workitem_id):
    """Delete a work item"""
    try:
        work_item = WorkItem.query.get_or_404(workitem_id)
        project_id = work_item.project_id
        db.session.delete(work_item)
        db.session.commit()
        flash('Work item deleted successfully.', 'success')
        return redirect(url_for('project_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting work item: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))


@app.route('/api/task/add', methods=['POST'])
@login_required
def add_task():
    """Add a task to a project"""
    try:
        project_id = int(request.form.get('project_id'))
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')
        assigned_to_id = request.form.get('assigned_to_id')
        phase_id = request.form.get('phase_id')

        if not description:
            flash('Task description is required.', 'error')
            return redirect(url_for('project_detail', project_id=project_id))

        # Parse deadline
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        task = Task(
            project_id=project_id,
            description=description,
            deadline=deadline,
            assigned_to_id=int(assigned_to_id) if assigned_to_id else None,
            phase_id=int(phase_id) if phase_id else None
        )
        db.session.add(task)
        db.session.commit()

        flash('Task added successfully!', 'success')
        return redirect(url_for('project_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding task: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))


@app.route('/api/task/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_task(task_id):
    """Toggle task completion status, optionally logging a work item"""
    try:
        task = Task.query.get_or_404(task_id)
        task.toggle_completed()

        # If completing and hours/notes provided, create a work item
        hours = request.form.get('hours')
        notes = request.form.get('notes', '').strip()
        if task.completed and hours:
            hours_val = float(hours)
            if hours_val > 0:
                work_item = WorkItem(
                    project_id=task.project_id,
                    description=notes or f"Completed task: {task.description}",
                    hours=hours_val,
                    work_date=datetime.utcnow(),
                    created_by_id=current_user.id
                )
                db.session.add(work_item)

        db.session.commit()

        return jsonify({'success': True, 'completed': task.completed})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/task/<int:task_id>/dev-edit', methods=['POST'])
@login_required
def dev_edit_task(task_id):
    """Edit a task (for developers editing their own tasks)"""
    try:
        task = Task.query.get_or_404(task_id)
        project_id = task.project_id

        # Only the assigned developer can edit their own tasks
        if task.assigned_to_id != current_user.id:
            abort(403)

        description = request.form.get('description')
        deadline_str = request.form.get('deadline')

        if not description:
            flash('Task description is required.', 'error')
            return redirect(url_for('dev_project_view', project_id=project_id))

        task.description = description
        task.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('dev_project_view', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating task: {str(e)}', 'error')
        return redirect(url_for('dev_project_view', project_id=project_id))


@app.route('/api/task/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    """Delete a task"""
    try:
        task = Task.query.get_or_404(task_id)
        project_id = task.project_id
        db.session.delete(task)
        db.session.commit()
        flash('Task deleted successfully.', 'success')
        return redirect(url_for('project_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting task: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))


@app.route('/api/project/<int:project_id>/assign-developers', methods=['POST'])
@admin_required
def assign_developers(project_id):
    """Assign developers to a project"""
    try:
        project = Project.query.get_or_404(project_id)
        selected_ids = request.form.getlist('developer_ids')
        selected_ids = [int(uid) for uid in selected_ids]

        # Get the selected users
        new_devs = User.query.filter(User.id.in_(selected_ids)).all() if selected_ids else []

        # Sync assignments
        project.assigned_developers = new_devs
        db.session.commit()

        flash(f'Developer assignments updated for "{project.name}".', 'success')
        return redirect(url_for('project_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating assignments: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))


@app.route('/api/task/<int:task_id>/assign', methods=['POST'])
@admin_required
def assign_task(task_id):
    """Assign a task to a developer"""
    try:
        task = Task.query.get_or_404(task_id)
        assigned_to_id = request.form.get('assigned_to_id')
        task.assigned_to_id = int(assigned_to_id) if assigned_to_id else None
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/project/<int:project_id>/dev-view')
@dev_required
def dev_project_view(project_id):
    """Developer-focused project view showing only their tasks"""
    project = Project.query.get_or_404(project_id)
    my_tasks = Task.query.filter_by(project_id=project_id, assigned_to_id=current_user.id).order_by(Task.completed, Task.deadline).all()
    my_work_items = WorkItem.query.filter_by(project_id=project_id, created_by_id=current_user.id).order_by(WorkItem.work_date.desc()).all()
    dev_comments = ProjectComment.query.filter_by(project_id=project_id, page_type='dev').order_by(ProjectComment.created_at.desc()).all()
    phases = Phase.query.filter_by(project_id=project_id).order_by(Phase.sort_order).all()
    current_phase = Phase.query.filter_by(project_id=project_id, status='in_progress').first()
    return render_template('dev_project_view.html', project=project, tasks=my_tasks, work_items=my_work_items,
                           comments=dev_comments, phases=phases, current_phase=current_phase, now=datetime.now())


@app.route('/report/<int:project_id>')
@login_required
def generate_report(project_id):
    """Generate and download PDF report for a project"""
    try:
        project = Project.query.get_or_404(project_id)
        pdf_path = generate_project_report(project)
        return send_file(pdf_path, as_attachment=True, download_name=f'{project.name}_report.pdf')
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))


# =============================================================================
# BILLING & INVOICE ROUTES
# =============================================================================

@app.route('/billing')
@billing_required
def billing_dashboard():
    """Billing dashboard - display external projects with financial info"""
    show_archived = request.args.get('show_archived', '0') == '1'
    base_query = Project.query.filter_by(project_type='External')
    if not show_archived:
        base_query = base_query.filter(Project.status != 'archived')
    projects = base_query.order_by(Project.updated_at.desc()).all()
    clients = Client.query.order_by(Client.name).all()

    # Group projects by client name, sorted alphabetically (Unassigned last)
    from collections import OrderedDict
    raw_grouped = {}
    for project in projects:
        client_name = project.client.name if project.client else 'Unassigned'
        raw_grouped.setdefault(client_name, []).append(project)
    sorted_keys = sorted((k for k in raw_grouped if k != 'Unassigned'), key=str.lower)
    if 'Unassigned' in raw_grouped:
        sorted_keys.append('Unassigned')
    grouped = OrderedDict((k, raw_grouped[k]) for k in sorted_keys)

    # Build ready-to-invoice list: projects with completed (but not invoiced) phases or uninvoiced expenses
    ready_to_invoice = []
    for project in projects:
        completed_phases = [p for p in project.phases if p.status == 'completed']
        uninvoiced_expenses = [e for e in project.expenses if not e.invoiced]
        if completed_phases or uninvoiced_expenses:
            ready_to_invoice.append({
                'project': project,
                'phases': completed_phases,
                'expenses': uninvoiced_expenses,
                'phase_total': sum(p.amount for p in completed_phases),
                'expense_total': sum(e.amount for e in uninvoiced_expenses),
            })

    return render_template('billing_dashboard.html', projects=projects, grouped_projects=grouped, clients=clients, show_archived=show_archived, ready_to_invoice=ready_to_invoice)


@app.route('/billing/<int:project_id>')
@billing_required
def billing_detail(project_id):
    """Billing detail page for a project"""
    project = Project.query.get_or_404(project_id)
    invoices = Invoice.query.filter_by(project_id=project_id).order_by(Invoice.invoice_date.desc()).all()
    billing_comments = ProjectComment.query.filter_by(project_id=project_id, page_type='billing').order_by(ProjectComment.created_at.desc()).all()
    phases = Phase.query.filter_by(project_id=project_id).order_by(Phase.sort_order).all()
    project_links = ProjectLink.query.filter_by(project_id=project_id).order_by(ProjectLink.created_at.desc()).all()
    expenses = Expense.query.filter_by(project_id=project_id).order_by(Expense.expense_date.desc()).all()
    clients = Client.query.order_by(Client.name).all()
    return render_template('billing_detail.html', project=project, invoices=invoices, comments=billing_comments,
                           phases=phases, project_links=project_links, expenses=expenses, clients=clients, now=datetime.now())


@app.route('/api/project/<int:project_id>/update-info', methods=['POST'])
@billing_required
def update_project_info(project_id):
    """Update project info, billing, and notes"""
    try:
        project = Project.query.get_or_404(project_id)

        # Project info fields
        project.name = request.form.get('name', '').strip() or project.name
        project.description = request.form.get('description', '').strip() or None
        project.project_type = request.form.get('project_type', 'External')
        project.hours_budget = float(request.form.get('hours_budget', 0) or 0)
        start_date_str = request.form.get('start_date', '').strip()
        project.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None

        # Client
        new_client_name = request.form.get('new_client_name', '').strip()
        if new_client_name:
            client = Client.query.filter_by(name=new_client_name).first()
            if not client:
                client = Client(name=new_client_name)
                db.session.add(client)
                db.session.flush()
            project.client_id = client.id
        else:
            client_id = request.form.get('client_id', '').strip()
            project.client_id = int(client_id) if client_id else None

        # Billing fields
        project.halo_link = request.form.get('halo_link', '').strip() or None
        project.billing_client = request.form.get('billing_client', '').strip() or None
        project.billing_for = request.form.get('billing_for', '').strip() or None
        project.proposal_amount = float(request.form.get('proposal_amount', 0) or 0)
        project.monthly_support_hours = float(request.form.get('monthly_support_hours', 0) or 0)
        project.monthly_support_amount = float(request.form.get('monthly_support_amount', 0) or 0)
        # Auto-toggle recurring when support values are set; sync monthly_amount
        if project.monthly_support_amount > 0 or project.monthly_support_hours > 0:
            project.is_recurring = True
            project.monthly_amount = project.monthly_support_amount
        else:
            project.is_recurring = request.form.get('is_recurring') == 'on'
            project.monthly_amount = float(request.form.get('monthly_amount', 0) or 0)
        project.project_notes = request.form.get('project_notes', '').strip() or None
        project.hourly_cost_rate = float(request.form.get('hourly_cost_rate', 0) or 0)

        db.session.commit()
        flash('Project info updated successfully!', 'success')
        redirect_to = request.form.get('redirect_to', 'billing')
        if redirect_to == 'dev':
            return redirect(url_for('project_detail', project_id=project_id))
        return redirect(url_for('billing_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating project info: {str(e)}', 'error')
        redirect_to = request.form.get('redirect_to', 'billing')
        if redirect_to == 'dev':
            return redirect(url_for('project_detail', project_id=project_id))
        return redirect(url_for('billing_detail', project_id=project_id))


@app.route('/api/invoice/add', methods=['POST'])
@billing_required
def add_invoice():
    """Add an invoice to a project"""
    try:
        project_id = int(request.form.get('project_id'))
        invoice_number = request.form.get('invoice_number', '').strip()
        amount = float(request.form.get('amount', 0))
        description = request.form.get('description', '').strip()
        invoice_date_str = request.form.get('invoice_date')

        if amount <= 0:
            flash('Invoice amount must be greater than zero.', 'error')
            return redirect(url_for('billing_detail', project_id=project_id))

        invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date() if invoice_date_str else date.today()

        invoice = Invoice(
            project_id=project_id,
            invoice_number=invoice_number or None,
            amount=amount,
            invoice_date=invoice_date,
            description=description or None
        )
        db.session.add(invoice)
        db.session.commit()

        flash('Invoice added successfully!', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding invoice: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


@app.route('/api/invoice/<int:invoice_id>/edit', methods=['POST'])
@billing_required
def edit_invoice(invoice_id):
    """Edit an invoice"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        project_id = invoice.project_id

        invoice.invoice_number = request.form.get('invoice_number', '').strip() or None
        invoice.amount = float(request.form.get('amount', 0))
        invoice.description = request.form.get('description', '').strip() or None
        invoice_date_str = request.form.get('invoice_date')
        if invoice_date_str:
            invoice.invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()

        db.session.commit()
        flash('Invoice updated successfully!', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating invoice: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


@app.route('/api/invoice/<int:invoice_id>/delete', methods=['POST'])
@billing_required
def delete_invoice(invoice_id):
    """Delete an invoice"""
    try:
        invoice = Invoice.query.get_or_404(invoice_id)
        project_id = invoice.project_id
        db.session.delete(invoice)
        db.session.commit()
        flash('Invoice deleted successfully.', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting invoice: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


# =============================================================================
# EXPENSE ROUTES
# =============================================================================

@app.route('/api/expense/add', methods=['POST'])
@billing_required
def add_expense():
    """Add an expense to a project"""
    try:
        project_id = int(request.form.get('project_id'))
        description = request.form.get('description', '').strip()
        amount = float(request.form.get('amount', 0))
        category = request.form.get('category', 'General').strip()
        expense_date_str = request.form.get('expense_date')

        if not description:
            flash('Expense description is required.', 'error')
            return redirect(url_for('billing_detail', project_id=project_id))

        if amount <= 0:
            flash('Expense amount must be greater than zero.', 'error')
            return redirect(url_for('billing_detail', project_id=project_id))

        expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d').date() if expense_date_str else date.today()

        link = request.form.get('link', '').strip() or None

        expense = Expense(
            project_id=project_id,
            description=description,
            amount=amount,
            category=category or 'General',
            expense_date=expense_date,
            link=link
        )
        db.session.add(expense)
        db.session.commit()

        flash('Expense added successfully!', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding expense: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


@app.route('/api/expense/<int:expense_id>/edit', methods=['POST'])
@billing_required
def edit_expense(expense_id):
    """Edit an expense"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        project_id = expense.project_id

        expense.description = request.form.get('description', '').strip()
        expense.amount = float(request.form.get('amount', 0))
        expense.category = request.form.get('category', 'General').strip() or 'General'
        expense.link = request.form.get('link', '').strip() or None
        expense.invoiced = request.form.get('invoiced') == 'on'
        expense_date_str = request.form.get('expense_date')
        if expense_date_str:
            expense.expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d').date()

        db.session.commit()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating expense: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


@app.route('/api/expense/<int:expense_id>/delete', methods=['POST'])
@billing_required
def delete_expense(expense_id):
    """Delete an expense"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        project_id = expense.project_id
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted successfully.', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting expense: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


@app.route('/api/expense/<int:expense_id>/toggle-invoiced', methods=['POST'])
@billing_required
def toggle_expense_invoiced(expense_id):
    """Toggle an expense's invoiced status"""
    try:
        expense = Expense.query.get_or_404(expense_id)
        project_id = expense.project_id
        expense.invoiced = not expense.invoiced
        db.session.commit()
        flash(f'Expense marked as {"invoiced" if expense.invoiced else "uninvoiced"}.', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating expense: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


# =============================================================================
# ARCHIVE ROUTES
# =============================================================================

@app.route('/api/project/<int:project_id>/archive', methods=['POST'])
@admin_required
def archive_project(project_id):
    """Archive a project"""
    try:
        project = Project.query.get_or_404(project_id)
        project.status = 'archived'
        project.archived_at = datetime.utcnow()
        db.session.commit()
        flash(f'Project "{project.name}" has been archived.', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error archiving project: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))


@app.route('/api/project/<int:project_id>/unarchive', methods=['POST'])
@admin_required
def unarchive_project(project_id):
    """Unarchive a project"""
    try:
        project = Project.query.get_or_404(project_id)
        project.status = 'active'
        project.archived_at = None
        db.session.commit()
        flash(f'Project "{project.name}" has been restored.', 'success')
        return redirect(url_for('project_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error restoring project: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))


@app.route('/api/project/<int:project_id>/hold', methods=['POST'])
@billing_required
def hold_project(project_id):
    """Put a project on hold"""
    try:
        project = Project.query.get_or_404(project_id)
        project.status = 'on_hold'
        db.session.commit()
        flash(f'Project "{project.name}" has been put on hold.', 'info')
        redirect_to = request.form.get('redirect_to', 'billing')
        if redirect_to == 'dev':
            return redirect(url_for('project_detail', project_id=project_id))
        return redirect(url_for('billing_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating project: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


@app.route('/api/project/<int:project_id>/reactivate', methods=['POST'])
@billing_required
def reactivate_project(project_id):
    """Reactivate a project from on hold"""
    try:
        project = Project.query.get_or_404(project_id)
        project.status = 'active'
        db.session.commit()
        flash(f'Project "{project.name}" has been reactivated.', 'success')
        redirect_to = request.form.get('redirect_to', 'billing')
        if redirect_to == 'dev':
            return redirect(url_for('project_detail', project_id=project_id))
        return redirect(url_for('billing_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating project: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


# =============================================================================
# CLIENT ROUTES
# =============================================================================

@app.route('/clients')
@admin_required
def client_management():
    """Client management page"""
    clients = Client.query.order_by(Client.name).all()
    return render_template('client_management.html', clients=clients)


@app.route('/api/client/create', methods=['POST'])
@login_required
def create_client():
    """Create a new client"""
    try:
        name = request.form.get('name', '').strip()
        if not name:
            flash('Client name is required.', 'error')
            return redirect(request.referrer or url_for('home'))

        existing = Client.query.filter_by(name=name).first()
        if existing:
            flash(f'Client "{name}" already exists.', 'error')
            return redirect(request.referrer or url_for('home'))

        client = Client(
            name=name,
            contact_name=request.form.get('contact_name', '').strip() or None,
            contact_email=request.form.get('contact_email', '').strip() or None,
            contact_phone=request.form.get('contact_phone', '').strip() or None,
        )
        db.session.add(client)
        db.session.commit()
        flash(f'Client "{name}" created successfully!', 'success')
        return redirect(request.referrer or url_for('client_management'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating client: {str(e)}', 'error')
        return redirect(request.referrer or url_for('home'))


@app.route('/api/client/<int:client_id>/update', methods=['POST'])
@admin_required
def update_client(client_id):
    """Update a client"""
    client = Client.query.get_or_404(client_id)
    try:
        name = request.form.get('name', '').strip()
        if not name:
            flash('Client name is required.', 'error')
            return redirect(url_for('client_management'))

        existing = Client.query.filter(Client.name == name, Client.id != client_id).first()
        if existing:
            flash(f'Client "{name}" already exists.', 'error')
            return redirect(url_for('client_management'))

        client.name = name
        client.contact_name = request.form.get('contact_name', '').strip() or None
        client.contact_email = request.form.get('contact_email', '').strip() or None
        client.contact_phone = request.form.get('contact_phone', '').strip() or None
        db.session.commit()
        flash(f'Client "{name}" updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating client: {str(e)}', 'error')
    return redirect(url_for('client_management'))


@app.route('/api/client/<int:client_id>/delete', methods=['POST'])
@admin_required
def delete_client(client_id):
    """Delete a client"""
    client = Client.query.get_or_404(client_id)
    try:
        if client.projects:
            flash(f'Cannot delete "{client.name}" — it has {len(client.projects)} project(s) assigned.', 'error')
            return redirect(url_for('client_management'))
        name = client.name
        db.session.delete(client)
        db.session.commit()
        flash(f'Client "{name}" deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting client: {str(e)}', 'error')
    return redirect(url_for('client_management'))


# =============================================================================
# COMMENT ROUTES
# =============================================================================

@app.route('/api/comment/add', methods=['POST'])
@login_required
def add_comment():
    """Add a comment to a project"""
    try:
        project_id = int(request.form.get('project_id'))
        comment_text = request.form.get('comment', '').strip()
        page_type = request.form.get('page_type', 'dev')

        if not comment_text:
            flash('Comment cannot be empty.', 'error')
            if page_type == 'billing':
                return redirect(url_for('billing_detail', project_id=project_id))
            return redirect(url_for('project_detail', project_id=project_id))

        comment = ProjectComment(
            project_id=project_id,
            user_id=current_user.id,
            comment=comment_text,
            page_type=page_type
        )
        db.session.add(comment)
        db.session.commit()
        flash('Comment added!', 'success')

        # Redirect back to the page they came from
        if request.referrer:
            return redirect(request.referrer)
        if page_type == 'billing':
            return redirect(url_for('billing_detail', project_id=project_id))
        return redirect(url_for('project_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding comment: {str(e)}', 'error')
        return redirect(request.referrer or url_for('home'))


@app.route('/api/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    """Delete a comment (admin or author only)"""
    try:
        comment = ProjectComment.query.get_or_404(comment_id)
        project_id = comment.project_id
        page_type = comment.page_type

        if not current_user.is_admin and comment.user_id != current_user.id:
            abort(403)

        db.session.delete(comment)
        db.session.commit()
        flash('Comment deleted.', 'success')

        if request.referrer:
            return redirect(request.referrer)
        if page_type == 'billing':
            return redirect(url_for('billing_detail', project_id=project_id))
        return redirect(url_for('project_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting comment: {str(e)}', 'error')
        return redirect(request.referrer or url_for('home'))


# =============================================================================
# PHASE ROUTES
# =============================================================================

@app.route('/api/phase/add', methods=['POST'])
@admin_required
def add_phase():
    """Add a phase to a project"""
    try:
        project_id = int(request.form.get('project_id'))
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        amount = float(request.form.get('amount', 0) or 0)
        hours_budget = float(request.form.get('hours_budget', 0) or 0)
        is_extension = request.form.get('is_extension') == 'on'
        redirect_to = request.form.get('redirect_to', 'billing')

        redirect_url = url_for('project_detail', project_id=project_id) if redirect_to == 'dev' else url_for('billing_detail', project_id=project_id)

        if not name:
            flash('Phase name is required.', 'error')
            return redirect(redirect_url)

        # Get next sort order
        max_order = db.session.query(db.func.max(Phase.sort_order)).filter_by(project_id=project_id).scalar() or 0

        link = request.form.get('link', '').strip() or None

        phase = Phase(
            project_id=project_id,
            name=name,
            description=description or None,
            amount=amount,
            hours_budget=hours_budget,
            is_extension=is_extension,
            link=link,
            sort_order=max_order + 1
        )
        db.session.add(phase)
        db.session.commit()
        flash(f'Phase "{name}" added!', 'success')
        return redirect(redirect_url)

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding phase: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=project_id))


@app.route('/api/phase/<int:phase_id>/edit', methods=['POST'])
@admin_required
def edit_phase(phase_id):
    """Edit a phase"""
    try:
        phase = Phase.query.get_or_404(phase_id)
        project_id = phase.project_id
        redirect_to = request.form.get('redirect_to', 'billing')

        phase.name = request.form.get('name', '').strip() or phase.name
        phase.description = request.form.get('description', '').strip() or None
        phase.amount = float(request.form.get('amount', 0) or 0)
        phase.hours_budget = float(request.form.get('hours_budget', 0) or 0)
        phase.is_extension = request.form.get('is_extension') == 'on'
        phase.link = request.form.get('link', '').strip() or None
        new_status = request.form.get('status')
        if new_status and new_status in Phase.STATUSES:
            phase.status = new_status

        redirect_url = url_for('project_detail', project_id=project_id) if redirect_to == 'dev' else url_for('billing_detail', project_id=project_id)

        db.session.commit()
        flash('Phase updated!', 'success')
        return redirect(redirect_url)
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating phase: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=phase.project_id))


@app.route('/api/phase/<int:phase_id>/delete', methods=['POST'])
@admin_required
def delete_phase(phase_id):
    """Delete a phase"""
    try:
        phase = Phase.query.get_or_404(phase_id)
        project_id = phase.project_id
        redirect_to = request.form.get('redirect_to', 'billing')
        redirect_url = url_for('project_detail', project_id=project_id) if redirect_to == 'dev' else url_for('billing_detail', project_id=project_id)
        db.session.delete(phase)
        db.session.commit()
        flash('Phase deleted.', 'success')
        return redirect(redirect_url)
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting phase: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=phase.project_id))


@app.route('/api/phase/<int:phase_id>/update-status', methods=['POST'])
@admin_required
def update_phase_status(phase_id):
    """Advance phase to next status"""
    try:
        phase = Phase.query.get_or_404(phase_id)
        project_id = phase.project_id
        new_status = request.form.get('status')
        redirect_to = request.form.get('redirect_to', 'billing')
        redirect_url = url_for('project_detail', project_id=project_id) if redirect_to == 'dev' else url_for('billing_detail', project_id=project_id)

        if new_status and new_status in Phase.STATUSES:
            phase.status = new_status
            db.session.commit()
            flash(f'Phase "{phase.name}" status updated to {phase.status_display}.', 'success')
        else:
            flash('Invalid status.', 'error')

        return redirect(redirect_url)
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating phase status: {str(e)}', 'error')
        return redirect(url_for('project_detail', project_id=phase.project_id))


# =============================================================================
# PROJECT LINK ROUTES
# =============================================================================

@app.route('/api/link/add', methods=['POST'])
@billing_required
def add_link():
    """Add a link to a project"""
    try:
        project_id = int(request.form.get('project_id'))
        title = request.form.get('title', '').strip()
        url = request.form.get('url', '').strip()

        if not title or not url:
            flash('Link title and URL are required.', 'error')
            return redirect(url_for('billing_detail', project_id=project_id))

        link = ProjectLink(project_id=project_id, title=title, url=url)
        db.session.add(link)
        db.session.commit()
        flash('Link added!', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding link: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


@app.route('/api/link/<int:link_id>/delete', methods=['POST'])
@billing_required
def delete_link(link_id):
    """Delete a project link"""
    try:
        link = ProjectLink.query.get_or_404(link_id)
        project_id = link.project_id
        db.session.delete(link)
        db.session.commit()
        flash('Link deleted.', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting link: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=link.project_id))


# =============================================================================
# PROPOSAL UPLOAD & AI PROCESSING
# =============================================================================

@app.route('/api/project/<int:project_id>/upload-proposal', methods=['POST'])
@billing_required
def upload_proposal(project_id):
    """Upload a proposal PDF to a project"""
    try:
        project = Project.query.get_or_404(project_id)

        if 'proposal_file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('billing_detail', project_id=project_id))

        file = request.files['proposal_file']
        if not file or not file.filename:
            flash('No file selected.', 'error')
            return redirect(url_for('billing_detail', project_id=project_id))

        if not allowed_file(file.filename):
            flash('Only PDF files are allowed.', 'error')
            return redirect(url_for('billing_detail', project_id=project_id))

        from werkzeug.utils import secure_filename
        filename = secure_filename(f"project_{project.id}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        project.proposal_file_path = filename
        db.session.commit()

        flash('Proposal uploaded successfully!', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error uploading proposal: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


@app.route('/api/project/<int:project_id>/process-proposal', methods=['POST'])
@billing_required
def process_proposal(project_id):
    """Process uploaded proposal with AI to extract phases"""
    try:
        project = Project.query.get_or_404(project_id)

        if not project.proposal_file_path:
            flash('No proposal file uploaded yet.', 'error')
            return redirect(url_for('billing_detail', project_id=project_id))

        filepath = os.path.join(app.config['UPLOAD_FOLDER'], project.proposal_file_path)
        if not os.path.exists(filepath):
            flash('Proposal file not found.', 'error')
            return redirect(url_for('billing_detail', project_id=project_id))

        from proposal_parser import parse_proposal
        result = parse_proposal(filepath)

        if not result or not result.get('phases'):
            flash('Could not extract phases from proposal. Try adding them manually.', 'warning')
            return redirect(url_for('billing_detail', project_id=project_id))

        # Create phases from AI result
        max_order = db.session.query(db.func.max(Phase.sort_order)).filter_by(project_id=project_id).scalar() or 0
        phases_created = 0

        for i, phase_data in enumerate(result['phases']):
            phase = Phase(
                project_id=project_id,
                name=phase_data.get('name', f'Phase {i+1}'),
                description=phase_data.get('description'),
                amount=float(phase_data.get('amount', 0)),
                hours_budget=float(phase_data.get('hours', 0)),
                sort_order=max_order + i + 1
            )
            db.session.add(phase)
            phases_created += 1

        # Update project billing info if extracted
        if result.get('proposal_amount') and not project.proposal_amount:
            project.proposal_amount = float(result['proposal_amount'])
        if result.get('billing_client') and not project.billing_client:
            project.billing_client = result['billing_client']

        db.session.commit()
        flash(f'Successfully extracted {phases_created} phase(s) from proposal!', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error processing proposal: {str(e)}', 'error')
        return redirect(url_for('billing_detail', project_id=project_id))


@app.route('/download/proposal/<int:project_id>')
@login_required
def download_proposal(project_id):
    """Download the proposal file for a project"""
    project = Project.query.get_or_404(project_id)
    if not project.proposal_file_path:
        flash('No proposal file available.', 'error')
        return redirect(request.referrer or url_for('home'))

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], project.proposal_file_path)
    if not os.path.exists(filepath):
        flash('Proposal file not found.', 'error')
        return redirect(request.referrer or url_for('home'))

    return send_file(filepath, as_attachment=True, download_name=project.proposal_file_path)


# =============================================================================
# LEAD ROUTES
# =============================================================================

@app.route('/lead/<int:lead_id>')
@login_required
def lead_detail(lead_id):
    """Lead detail page"""
    lead = Lead.query.get_or_404(lead_id)
    notes = LeadNote.query.filter_by(lead_id=lead_id).order_by(LeadNote.created_at.desc()).all()
    tasks = LeadTask.query.filter_by(lead_id=lead_id).order_by(LeadTask.completed, LeadTask.deadline).all()
    return render_template('lead_detail.html', lead=lead, notes=notes, tasks=tasks, now=datetime.now())


@app.route('/api/lead/create', methods=['POST'])
@login_required
def create_lead():
    """Create a new lead"""
    try:
        name = request.form.get('name')
        description = request.form.get('description', '')
        estimated_hours = float(request.form.get('estimated_hours', 0))
        status = request.form.get('status', 'New')

        if not name:
            flash('Lead name is required.', 'error')
            return redirect(url_for('home'))

        lead = Lead(
            name=name,
            description=description,
            estimated_hours=estimated_hours,
            status=status
        )
        db.session.add(lead)
        db.session.commit()

        flash(f'Lead "{name}" created successfully!', 'success')
        return redirect(url_for('lead_detail', lead_id=lead.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating lead: {str(e)}', 'error')
        return redirect(url_for('home'))


@app.route('/api/lead/<int:lead_id>/delete', methods=['POST'])
@login_required
def delete_lead(lead_id):
    """Delete a lead"""
    try:
        lead = Lead.query.get_or_404(lead_id)
        lead_name = lead.name
        db.session.delete(lead)
        db.session.commit()
        flash(f'Lead "{lead_name}" deleted successfully.', 'success')
        return redirect(url_for('home'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting lead: {str(e)}', 'error')
        return redirect(url_for('home'))


@app.route('/api/lead/<int:lead_id>/convert', methods=['POST'])
@login_required
def convert_lead_to_project(lead_id):
    """Convert a lead to a project, transferring all notes and tasks"""
    try:
        lead = Lead.query.get_or_404(lead_id)

        # Create new project from lead
        project = Project(
            name=lead.name,
            description=lead.description,
            hours_budget=lead.estimated_hours
        )
        db.session.add(project)
        db.session.flush()  # Get project ID without committing

        # Convert lead notes to work items
        for note in lead.notes:
            work_item = WorkItem(
                project_id=project.id,
                description=note.note,
                hours=note.hours,
                work_date=note.work_date
            )
            db.session.add(work_item)

        # Convert lead tasks to project tasks
        for lead_task in lead.tasks:
            task = Task(
                project_id=project.id,
                description=lead_task.description,
                deadline=lead_task.deadline,
                completed=lead_task.completed,
                completed_at=lead_task.completed_at
            )
            db.session.add(task)

        # Delete the lead (cascade will delete notes and tasks)
        db.session.delete(lead)
        db.session.commit()

        flash(f'Lead "{lead.name}" successfully converted to project!', 'success')
        return redirect(url_for('project_detail', project_id=project.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error converting lead: {str(e)}', 'error')
        return redirect(url_for('lead_detail', lead_id=lead_id))


@app.route('/api/leadnote/add', methods=['POST'])
@login_required
def add_lead_note():
    """Add a note to a lead"""
    try:
        lead_id = int(request.form.get('lead_id'))
        note = request.form.get('note')
        hours = float(request.form.get('hours', 0))
        work_date_str = request.form.get('work_date')

        if not note:
            flash('Note is required.', 'error')
            return redirect(url_for('lead_detail', lead_id=lead_id))

        # Parse work date
        work_date = datetime.strptime(work_date_str, '%Y-%m-%d') if work_date_str else datetime.utcnow()

        lead_note = LeadNote(
            lead_id=lead_id,
            note=note,
            hours=hours,
            work_date=work_date
        )
        db.session.add(lead_note)
        db.session.commit()

        flash('Note added successfully!', 'success')
        return redirect(url_for('lead_detail', lead_id=lead_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding note: {str(e)}', 'error')
        return redirect(url_for('lead_detail', lead_id=lead_id))


@app.route('/api/leadnote/<int:note_id>/edit', methods=['POST'])
@login_required
def edit_lead_note(note_id):
    """Edit a lead note"""
    try:
        lead_note = LeadNote.query.get_or_404(note_id)
        lead_id = lead_note.lead_id

        note = request.form.get('note')
        hours = float(request.form.get('hours', 0))
        work_date_str = request.form.get('work_date')

        if not note:
            flash('Note is required.', 'error')
            return redirect(url_for('lead_detail', lead_id=lead_id))

        lead_note.note = note
        lead_note.hours = hours
        if work_date_str:
            lead_note.work_date = datetime.strptime(work_date_str, '%Y-%m-%d')

        db.session.commit()
        flash('Note updated successfully!', 'success')
        return redirect(url_for('lead_detail', lead_id=lead_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating note: {str(e)}', 'error')
        return redirect(url_for('lead_detail', lead_id=lead_id))


@app.route('/api/leadnote/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_lead_note(note_id):
    """Delete a lead note"""
    try:
        lead_note = LeadNote.query.get_or_404(note_id)
        lead_id = lead_note.lead_id
        db.session.delete(lead_note)
        db.session.commit()
        flash('Note deleted successfully.', 'success')
        return redirect(url_for('lead_detail', lead_id=lead_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting note: {str(e)}', 'error')
        return redirect(url_for('lead_detail', lead_id=lead_id))


@app.route('/api/leadtask/add', methods=['POST'])
@login_required
def add_lead_task():
    """Add a task to a lead"""
    try:
        lead_id = int(request.form.get('lead_id'))
        description = request.form.get('description')
        deadline_str = request.form.get('deadline')

        if not description:
            flash('Task description is required.', 'error')
            return redirect(url_for('lead_detail', lead_id=lead_id))

        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        lead_task = LeadTask(
            lead_id=lead_id,
            description=description,
            deadline=deadline
        )
        db.session.add(lead_task)
        db.session.commit()

        flash('Task added successfully!', 'success')
        return redirect(url_for('lead_detail', lead_id=lead_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error adding task: {str(e)}', 'error')
        return redirect(url_for('lead_detail', lead_id=lead_id))


@app.route('/api/leadtask/<int:task_id>/toggle', methods=['POST'])
@login_required
def toggle_lead_task(task_id):
    """Toggle lead task completion status"""
    try:
        task = LeadTask.query.get_or_404(task_id)
        task.toggle_completed()
        db.session.commit()

        return jsonify({'success': True, 'completed': task.completed})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/leadtask/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_lead_task(task_id):
    """Delete a lead task"""
    try:
        task = LeadTask.query.get_or_404(task_id)
        lead_id = task.lead_id
        db.session.delete(task)
        db.session.commit()
        flash('Task deleted successfully.', 'success')
        return redirect(url_for('lead_detail', lead_id=lead_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting task: {str(e)}', 'error')
        return redirect(url_for('lead_detail', lead_id=lead_id))


# =============================================================================
# USER MANAGEMENT ROUTES
# =============================================================================

@app.route('/users')
@admin_required
def user_management():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('user_management.html', users=users)


@app.route('/api/user/create', methods=['POST'])
@admin_required
def create_user():
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        role = request.form.get('role', 'developer')
        is_admin = (role == 'admin')

        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('user_management'))

        if password != password_confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('user_management'))

        if User.query.filter_by(username=username).first():
            flash(f'User "{username}" already exists.', 'error')
            return redirect(url_for('user_management'))

        user = User(username=username, is_admin=is_admin, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f'User "{username}" created successfully!', 'success')
        return redirect(url_for('user_management'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'error')
        return redirect(url_for('user_management'))


@app.route('/api/user/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            flash('You cannot delete your own account.', 'error')
            return redirect(url_for('user_management'))

        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'User "{username}" deleted successfully.', 'success')
        return redirect(url_for('user_management'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        return redirect(url_for('user_management'))


@app.route('/api/user/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    try:
        user = User.query.get_or_404(user_id)
        new_password = request.form.get('new_password', '')
        new_password_confirm = request.form.get('new_password_confirm', '')

        if not new_password:
            flash('New password is required.', 'error')
            return redirect(url_for('user_management'))

        if new_password != new_password_confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('user_management'))

        user.set_password(new_password)
        db.session.commit()

        flash(f'Password for "{user.username}" reset successfully!', 'success')
        return redirect(url_for('user_management'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error resetting password: {str(e)}', 'error')
        return redirect(url_for('user_management'))


@app.route('/api/user/<int:user_id>/change-role', methods=['POST'])
@admin_required
def change_user_role(user_id):
    try:
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            flash('You cannot change your own role.', 'error')
            return redirect(url_for('user_management'))

        role = request.form.get('role', '')
        if role not in User.ROLES:
            flash('Invalid role selected.', 'error')
            return redirect(url_for('user_management'))

        user.role = role
        user.is_admin = (role == 'admin')
        db.session.commit()

        flash(f'Role for "{user.username}" changed to {role}.', 'success')
        return redirect(url_for('user_management'))

    except Exception as e:
        db.session.rollback()
        flash(f'Error changing role: {str(e)}', 'error')
        return redirect(url_for('user_management'))


# Template filters
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    """Format datetime for display"""
    if value is None:
        return ''
    return value.strftime(format)


@app.template_filter('dateformat')
def dateformat(value, format='%Y-%m-%d'):
    """Format date for display"""
    if value is None:
        return ''
    return value.strftime(format)


# CLI Commands for user management
@app.cli.command('create-user')
def create_user_command():
    """Create a new user via Flask CLI"""
    import getpass

    username = input('Username: ')
    password = getpass.getpass('Password: ')
    password_confirm = getpass.getpass('Confirm Password: ')

    if password != password_confirm:
        print('Passwords do not match!')
        return

    # Check if user exists
    if User.query.filter_by(username=username).first():
        print(f'User "{username}" already exists!')
        return

    user = User(username=username, is_admin=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    print(f'User "{username}" created successfully!')


@app.cli.command('init-db')
def init_db_command():
    """Initialize the database with tables"""
    db.create_all()
    print('Database initialized!')


if __name__ == '__main__':
    app.run(debug=True)
