from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_required, current_user
from datetime import datetime, date
from config import Config
from models import db, User, Project, WorkItem, Task, Lead, LeadNote, LeadTask
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


@app.route('/')
@login_required
def home():
    """Home page - display all projects and leads"""
    external_projects = Project.query.filter_by(project_type='External').order_by(Project.updated_at.desc()).all()
    internal_projects = Project.query.filter_by(project_type='Internal').order_by(Project.updated_at.desc()).all()
    leads = Lead.query.order_by(Lead.updated_at.desc()).all()
    return render_template('home.html', external_projects=external_projects, internal_projects=internal_projects, leads=leads)


@app.route('/project/<int:project_id>')
@login_required
def project_detail(project_id):
    """Project detail page"""
    project = Project.query.get_or_404(project_id)
    work_items = WorkItem.query.filter_by(project_id=project_id).order_by(WorkItem.work_date.desc()).all()
    tasks = Task.query.filter_by(project_id=project_id).order_by(Task.completed, Task.deadline).all()
    return render_template('project_detail.html', project=project, work_items=work_items, tasks=tasks, now=datetime.now())


@app.route('/api/project/create', methods=['POST'])
@login_required
def create_project():
    """Create a new project"""
    try:
        name = request.form.get('name')
        description = request.form.get('description', '')
        hours_budget = float(request.form.get('hours_budget', 0))
        project_type = request.form.get('project_type', 'External')

        if not name:
            flash('Project name is required.', 'error')
            return redirect(url_for('home'))

        project = Project(
            name=name,
            description=description,
            hours_budget=hours_budget,
            project_type=project_type
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
@login_required
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
@login_required
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

        if not description:
            flash('Task description is required.', 'error')
            return redirect(url_for('project_detail', project_id=project_id))

        # Parse deadline
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        task = Task(
            project_id=project_id,
            description=description,
            deadline=deadline
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


if __name__ == '__main__':
    app.run(debug=True)
