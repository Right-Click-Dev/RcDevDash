from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, abort
from flask_login import LoginManager, login_required, current_user
from datetime import datetime, date
from config import Config
from models import db, User, Project, WorkItem, Task, Lead, LeadNote, LeadTask, Invoice, project_assignments
from auth import auth_bp
from reports import generate_project_report

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

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


@app.route('/')
@login_required
def home():
    """Home page - display all projects and leads"""
    # Billing-only users get redirected to billing dashboard
    if not current_user.can_access_dev:
        return redirect(url_for('billing_dashboard'))

    # Developers only see projects they're assigned to
    if current_user.role == User.ROLE_DEVELOPER:
        assigned = current_user.assigned_projects
        external_projects = [p for p in assigned if p.project_type == 'External']
        internal_projects = [p for p in assigned if p.project_type == 'Internal']
        leads = []  # Developers don't manage leads
    else:
        external_projects = Project.query.filter_by(project_type='External').order_by(Project.updated_at.desc()).all()
        internal_projects = Project.query.filter_by(project_type='Internal').order_by(Project.updated_at.desc()).all()
        leads = Lead.query.order_by(Lead.updated_at.desc()).all()

    return render_template('home.html', external_projects=external_projects, internal_projects=internal_projects, leads=leads)


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
    return render_template('project_detail.html', project=project, work_items=work_items, tasks=tasks, developers=developers, now=datetime.now())


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

        if not name:
            flash('Project name is required.', 'error')
            return redirect(url_for('home'))

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
            monthly_amount=monthly_amount
        )
        db.session.add(project)
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
    """Edit a work item"""
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

        if not description:
            flash('Task description is required.', 'error')
            return redirect(url_for('project_detail', project_id=project_id))

        # Parse deadline
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        task = Task(
            project_id=project_id,
            description=description,
            deadline=deadline,
            assigned_to_id=int(assigned_to_id) if assigned_to_id else None
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
    """Toggle task completion status"""
    try:
        task = Task.query.get_or_404(task_id)
        task.toggle_completed()
        db.session.commit()

        return jsonify({'success': True, 'completed': task.completed})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


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
    return render_template('dev_project_view.html', project=project, tasks=my_tasks, now=datetime.now())


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
    projects = Project.query.filter_by(project_type='External').order_by(Project.updated_at.desc()).all()
    return render_template('billing_dashboard.html', projects=projects)


@app.route('/billing/<int:project_id>')
@billing_required
def billing_detail(project_id):
    """Billing detail page for a project"""
    project = Project.query.get_or_404(project_id)
    invoices = Invoice.query.filter_by(project_id=project_id).order_by(Invoice.invoice_date.desc()).all()
    return render_template('billing_detail.html', project=project, invoices=invoices, now=datetime.now())


@app.route('/api/project/<int:project_id>/update-info', methods=['POST'])
@billing_required
def update_project_info(project_id):
    """Update project billing info, Halo link, and notes"""
    try:
        project = Project.query.get_or_404(project_id)

        project.halo_link = request.form.get('halo_link', '').strip() or None
        project.billing_client = request.form.get('billing_client', '').strip() or None
        project.billing_for = request.form.get('billing_for', '').strip() or None
        project.proposal_amount = float(request.form.get('proposal_amount', 0) or 0)
        project.is_recurring = request.form.get('is_recurring') == 'on'
        project.monthly_amount = float(request.form.get('monthly_amount', 0) or 0)
        project.project_notes = request.form.get('project_notes', '').strip() or None

        db.session.commit()
        flash('Project info updated successfully!', 'success')
        return redirect(url_for('billing_detail', project_id=project_id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error updating project info: {str(e)}', 'error')
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
