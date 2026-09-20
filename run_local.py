"""
Lightweight local web application for Project Scheduler.
Uses Flask instead of Django for simpler local deployment.
All data stored in Excel files.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps

# Add project to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.excel_models import (
    User, Task, TaskStep, Project, AuditLog, TaskComment, TaskAttachment
)
from werkzeug.utils import secure_filename
from flask import send_from_directory
from core.scheduler_service import SchedulerService
from apscheduler.schedulers.background import BackgroundScheduler
from core.email_service import EmailService

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
app.config['EXCEL_STORAGE_DIR'] = BASE_DIR / 'excel_data'
app.config['UPLOAD_FOLDER'] = BASE_DIR / 'uploads'

# Initialize APScheduler
import atexit
scheduler = BackgroundScheduler()
scheduler.add_job(func=SchedulerService.check_and_send_reminders, trigger="interval", minutes=5)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


def login_required(f):
    """Decorator to require login for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get the currently logged-in user."""
    if 'user_id' in session:
        return User.get(session['user_id'])
    return None


def log_audit(action, entity_type, entity_id, description):
    """Log an audit entry."""
    user = get_current_user()
    audit = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:255]
    )
    audit.save()


# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/')
def index():
    """Home page - redirect to dashboard if logged in."""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password', 'danger')
            return render_template('simple_login.html')

        # Try to find user by username or email
        users = User.all()
        user = None
        for u in users:
            if u.username == username or u.email == username:
                user = u
                break

        if user and user.check_password(password):
            if not user.is_superuser:
                flash('Access denied. This system is restricted to administrators only.', 'danger')
                log_audit('login_failed', 'user', user.id, f'Non-admin user {username} attempted to log in')
                return render_template('simple_login.html')

            if user.is_active:
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_staff'] = user.is_staff
                session['is_superuser'] = user.is_superuser

                # Update last login
                user._data['last_login'] = datetime.now().isoformat()
                user.save()

                log_audit('login', 'user', user.id, f'User {user.username} logged in')
                flash(f'Welcome back, {user.full_name}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Your account is inactive. Please contact an administrator.', 'danger')
        else:
            flash('Invalid username or password', 'danger')
            log_audit('login_failed', 'user', None, f'Failed login attempt for: {username}')

    return render_template('simple_login.html')


@app.route('/logout')
def logout():
    """Logout."""
    user = get_current_user()
    if user:
        log_audit('logout', 'user', user.id, f'User {user.username} logged out')

    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))


# ============================================================================
# Dashboard Routes
# ============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard."""
    user = get_current_user()

    # Get statistics
    all_tasks = Task.all()
    my_tasks = [t for t in all_tasks if t.owner_id == user.id]

    all_steps = TaskStep.all()
    my_steps = [s for s in all_steps if s.assignee_id == user.id]

    # Status counts
    task_status_counts = {}
    for task in my_tasks:
        status = task.status or 'unknown'
        task_status_counts[status] = task_status_counts.get(status, 0) + 1

    # Overdue steps
    now = datetime.now()
    overdue_steps = []
    for step in my_steps:
        if step.status not in ['completed', 'cancelled'] and step.due_datetime:
            try:
                due = datetime.fromisoformat(step.due_datetime)
                if due < now:
                    overdue_steps.append(step)
            except:
                pass

    # Recent tasks
    recent_tasks = sorted(my_tasks, key=lambda t: t.created_at or '', reverse=True)[:5]

    # Upcoming steps (next 7 days)
    upcoming_steps = []
    future_date = now + timedelta(days=7)
    for step in my_steps:
        if step.status not in ['completed', 'cancelled'] and step.due_datetime:
            try:
                due = datetime.fromisoformat(step.due_datetime)
                if now <= due <= future_date:
                    upcoming_steps.append(step)
            except:
                pass

    return render_template('simple_dashboard.html',
                         user=user,
                         total_tasks=len(my_tasks),
                         total_steps=len(my_steps),
                         overdue_count=len(overdue_steps),
                         task_status_counts=task_status_counts,
                         recent_tasks=recent_tasks,
                         overdue_steps=overdue_steps,
                         upcoming_steps=upcoming_steps)


# ============================================================================
# Task Routes
# ============================================================================

@app.route('/tasks')
@login_required
def task_list():
    """List all tasks."""
    user = get_current_user()

    # Filter options
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    search = request.args.get('search', '').lower()

    # Get all tasks
    tasks = Task.all()

    # Apply filters
    if status_filter:
        tasks = [t for t in tasks if t.status == status_filter]
    if priority_filter:
        tasks = [t for t in tasks if t.priority == priority_filter]
    if search:
        tasks = [t for t in tasks if search in (t.title or '').lower() or search in (t.description or '').lower()]

    # Sort by created date
    tasks = sorted(tasks, key=lambda t: t.created_at or '', reverse=True)

    return render_template('simple_task_list.html',
                         user=user,
                         tasks=tasks,
                         status_filter=status_filter,
                         priority_filter=priority_filter,
                         search=search)


@app.route('/kanban')
@login_required
def kanban():
    """Kanban board view."""
    user = get_current_user()
    tasks = Task.all()
    
    # Group tasks by status
    grouped_tasks = {
        'draft': [],
        'not_started': [],
        'in_progress': [],
        'on_hold': [],
        'completed': []
    }
    
    for t in tasks:
        status = t.status or 'draft'
        if status in grouped_tasks:
            grouped_tasks[status].append(t)
        else:
            grouped_tasks['draft'].append(t)
            
    # Sort each group by priority/created_at
    for status in grouped_tasks:
        grouped_tasks[status].sort(key=lambda t: t.created_at or '', reverse=True)
        
    return render_template('simple_kanban.html', user=user, grouped_tasks=grouped_tasks)


@app.route('/timeline')
@login_required
def timeline():
    """Gantt/Timeline chart view."""
    user = get_current_user()
    tasks = Task.all()
    # We also want to fetch all steps (subtasks) to show in the timeline
    steps = TaskStep.all()
    
    return render_template('simple_timeline.html', user=user, tasks=tasks, steps=steps)


@app.route('/api/tasks/<task_id>/update_status', methods=['POST'])
@login_required
def api_task_update_status(task_id):
    """Update task status via API (for Kanban)."""
    task = Task.get(task_id)
    if not task:
        return jsonify({'success': False, 'message': 'Task not found'}), 404
        
    new_status = request.json.get('status')
    if new_status and new_status in ['draft', 'not_started', 'in_progress', 'on_hold', 'completed']:
        task._data['status'] = new_status
        if new_status == 'completed' and not task.completed_at:
            task._data['completed_at'] = datetime.now().isoformat()
            task._data['progress_percent'] = 100
        task.save()
        log_audit('update', 'task', task.id, f'Moved task "{task.title}" to {new_status}')
        return jsonify({'success': True})
        
    return jsonify({'success': False, 'message': 'Invalid status'}), 400


def get_unique_spocs():
    names = set()
    emails = set()
    for t in Task.all():
        if t.spoc_name: names.add(t.spoc_name)
        if t.spoc_email: emails.add(t.spoc_email)
    for s in TaskStep.all():
        if s.spoc_name: names.add(s.spoc_name)
        if s.spoc_email: emails.add(s.spoc_email)
    return sorted(list(names)), sorted(list(emails))

@app.route('/tasks/new', methods=['GET', 'POST'])
@login_required
def task_new():
    """Create a new task."""
    user = get_current_user()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'medium')
        status = request.form.get('status', 'draft')
        spoc_name = request.form.get('spoc_name', '').strip()
        spoc_email = request.form.get('spoc_email', '').strip()
        spoc_dept = request.form.get('spoc_dept', '').strip()
        start_date = request.form.get('start_date', '')
        due_date = request.form.get('due_date', '')

        if not title:
            flash('Task title is required', 'danger')
            return redirect(url_for('task_new'))
            
        # Prevent duplicate tasks
        if any(t.title.lower() == title.lower() for t in Task.all()):
            flash(f'A task with the title "{title}" already exists.', 'danger')
            return redirect(url_for('task_new'))

        # Create task
        task = Task(
            title=title,
            description=description,
            owner_id=user.id,
            created_by_id=user.id,
            status=status,
            priority=priority,
            spoc_name=spoc_name,
            spoc_email=spoc_email,
            spoc_dept=spoc_dept,
            progress_percent=0,
            start_date=start_date if start_date else None,
            due_date=due_date if due_date else None,
            enable_reminders=False
        )
        task.save()

        log_audit('create', 'task', task.id, f'Created task: {title}')
        flash(f'Task "{title}" created successfully!', 'success')
        return redirect(url_for('task_detail', task_id=task.id))

    spoc_names, spoc_emails = get_unique_spocs()
    return render_template('simple_task_form.html',
                         user=user,
                         task=None,
                         users=User.all(),
                         spoc_names=spoc_names,
                         spoc_emails=spoc_emails)


@app.route('/tasks/<task_id>')
@login_required
def task_detail(task_id):
    """View task details."""
    user = get_current_user()
    task = Task.get(task_id)

    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('task_list'))

    # Get steps for this task
    steps = TaskStep.filter(task_id=task_id)
    steps = sorted(steps, key=lambda s: s.order or 0)
    
    # Get comments for this task
    comments = TaskComment.filter(task_id=task_id)
    comments = sorted(comments, key=lambda c: c.created_at or '')
    
    # Get attachments for this task
    attachments = TaskAttachment.filter(task_id=task_id)
    attachments = sorted(attachments, key=lambda a: a.created_at or '', reverse=True)

    # Get Audit Logs for Task and Subtasks
    all_logs = AuditLog.all()
    step_ids = [s.id for s in steps]
    
    # Filter logs related to this task or its subtasks
    audit_logs = [
        log for log in all_logs 
        if (log.entity_type == 'task' and log.entity_id == task_id) or 
           (log.entity_type == 'subtask' and log.entity_id in step_ids) or
           (log.entity_type == 'task_comment' and log.description.endswith(task.title)) or
           (log.entity_type == 'task_attachment' and log.description.endswith(task.title))
    ]
    
    # Sort logs newest first
    audit_logs = sorted(audit_logs, key=lambda l: l.created_at or '', reverse=True)
    
    # Fetch user for each log to resolve full_name
    all_users = User.all()
    user_dict = {u.id: u.full_name for u in all_users}
    for log in audit_logs:
        log.user_full_name = user_dict.get(log.user_id, 'System')

    # Get owner
    owner = User.get(task.owner_id) if task.owner_id else None

    return render_template('simple_task_detail.html',
                         user=user,
                         task=task,
                         steps=steps,
                         comments=comments,
                         attachments=attachments,
                         owner=owner,
                         audit_logs=audit_logs)


@app.route('/tasks/<task_id>/export_log')
@login_required
def export_task_log(task_id):
    """Export task audit logs to CSV (Excel compatible)."""
    import csv
    import io
    from flask import Response
    
    task = Task.get(task_id)
    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('task_list'))

    steps = TaskStep.filter(task_id=task_id)
    step_ids = [s.id for s in steps]
    
    all_logs = AuditLog.all()
    audit_logs = [
        log for log in all_logs 
        if (log.entity_type == 'task' and log.entity_id == task_id) or 
           (log.entity_type == 'subtask' and log.entity_id in step_ids) or
           (log.entity_type == 'task_comment' and log.description.endswith(task.title)) or
           (log.entity_type == 'task_attachment' and log.description.endswith(task.title))
    ]
    audit_logs = sorted(audit_logs, key=lambda l: l.created_at or '', reverse=True)
    
    all_users = User.all()
    user_dict = {u.id: u.full_name for u in all_users}

    output = io.StringIO()
    writer = csv.writer(output)
    
    # CSV Header
    writer.writerow(['Timestamp', 'User', 'Action', 'Entity Type', 'Description'])
    
    # CSV Data rows
    for log in audit_logs:
        user_name = user_dict.get(log.user_id, 'System')
        writer.writerow([
            log.created_at,
            user_name,
            log.action,
            log.entity_type,
            log.description
        ])
    
    response = Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=task_{task_id}_history.csv"}
    )
    return response


@app.route('/tasks/<task_id>/edit', methods=['GET', 'POST'])
@login_required
def task_edit(task_id):
    """Edit a task."""
    user = get_current_user()
    task = Task.get(task_id)

    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('task_list'))

    if request.method == 'POST':
        task._data['title'] = request.form.get('title', '').strip()
        task._data['description'] = request.form.get('description', '').strip()
        task._data['priority'] = request.form.get('priority', 'medium')
        task._data['status'] = request.form.get('status', 'draft')
        task._data['spoc_name'] = request.form.get('spoc_name', '').strip()
        task._data['spoc_email'] = request.form.get('spoc_email', '').strip()
        task._data['spoc_dept'] = request.form.get('spoc_dept', '').strip()
        task._data['start_date'] = request.form.get('start_date', '') or None
        task._data['due_date'] = request.form.get('due_date', '') or None

        if not task._data['title']:
            flash('Task title is required', 'danger')
            return redirect(url_for('task_edit', task_id=task_id))

        task.save()

        log_audit('update', 'task', task.id, f'Updated task: {task._data["title"]}')
        flash('Task updated successfully!', 'success')
        return redirect(url_for('task_detail', task_id=task_id))

    return render_template('simple_task_form.html',
                         user=user,
                         task=task)


@app.route('/tasks/<task_id>/delete', methods=['POST'])
@login_required
def task_delete(task_id):
    """Delete a task."""
    task = Task.get(task_id)

    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('task_list'))

    # Delete all steps first
    steps = TaskStep.filter(task_id=task_id)
    for step in steps:
        step.delete()

    # Delete task
    title = task.title
    task.delete()

    log_audit('delete', 'task', task_id, f'Deleted task: {title}')
    flash(f'Task "{title}" deleted successfully', 'success')
    return redirect(url_for('task_list'))


@app.route('/tasks/<task_id>/comment', methods=['POST'])
@login_required
def task_comment(task_id):
    """Add a comment to a task."""
    user = get_current_user()
    task = Task.get(task_id)
    
    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('task_list'))
        
    content = request.form.get('content', '').strip()
    if content:
        comment = TaskComment(
            task_id=task_id,
            author_id=user.id,
            content=content,
            created_at=datetime.now().isoformat()
        )
        comment.save()
        log_audit('create', 'task_comment', comment.id, f'Added comment to task: {task.title}')
        flash('Comment added successfully!', 'success')
    else:
        flash('Comment cannot be empty', 'warning')
        
    return redirect(url_for('task_detail', task_id=task_id))


@app.route('/tasks/<task_id>/upload', methods=['POST'])
@login_required
def task_upload(task_id):
    """Upload a file attachment to a task."""
    user = get_current_user()
    task = Task.get(task_id)
    
    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('task_list'))
        
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))
        
    if file:
        filename = secure_filename(file.filename)
        # Add timestamp to make filename unique
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        unique_filename = timestamp + filename
        
        # Ensure uploads dir exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        attachment = TaskAttachment(
            task_id=task_id,
            uploader_id=user.id,
            filename=filename,
            file_path=unique_filename,
            created_at=datetime.now().isoformat()
        )
        attachment.save()
        log_audit('upload', 'task_attachment', attachment.id, f'Uploaded file {filename} to task: {task.title}')
        flash('File uploaded successfully!', 'success')
        
    return redirect(url_for('task_detail', task_id=task_id))


@app.route('/uploads/<filename>')
@login_required
def download_file(filename):
    """Download an uploaded file."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/tasks/<task_id>/send_custom_email', methods=['POST'])
@login_required
def task_send_custom_email(task_id):
    """Send a custom email regarding a task."""
    task = Task.get(task_id)
    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('task_list'))
        
    recipient = request.form.get('recipient', '').strip()
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    
    if not recipient or not subject or not body:
        flash('Recipient, Subject, and Body are required.', 'danger')
        return redirect(url_for('task_detail', task_id=task_id))
        
    # Send email using EmailService
    success, log = EmailService.send_email(
        recipient=recipient,
        subject=subject,
        body=body
    )
    
    if success:
        log_audit('email_sent', 'task', task.id, f'Custom email sent to {recipient} with subject "{subject}"')
        flash(f'Email sent successfully to {recipient}!', 'success')
    else:
        flash(f'Failed to send email to {recipient}. Check logs.', 'danger')
        
    return redirect(url_for('task_detail', task_id=task_id))

# ============================================================================
# Subtask Routes
# ============================================================================

@app.route('/tasks/<task_id>/subtasks/new', methods=['GET', 'POST'])
@login_required
def step_new(task_id):
    """Create a new subtask."""
    user = get_current_user()
    task = Task.get(task_id)

    if not task:
        flash('Task not found', 'danger')
        return redirect(url_for('task_list'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        assignee_id = request.form.get('assignee_id')
        spoc_name = request.form.get('spoc_name', '').strip()
        spoc_email = request.form.get('spoc_email', '').strip()
        spoc_custom_message = request.form.get('spoc_custom_message', '').strip()
        estimated_tat_days = request.form.get('estimated_tat_days')
        start_datetime = request.form.get('start_datetime', '')
        due_datetime = request.form.get('due_datetime', '')
        notify_on_start = request.form.get('notify_on_start') == 'yes'

        if not title:
            flash('Subtask title is required', 'danger')
            return redirect(url_for('step_new', task_id=task_id))
            
        # Prevent duplicate subtasks
        steps = TaskStep.filter(task_id=task_id)
        if any(s.title.lower() == title.lower() for s in steps):
            flash(f'A subtask with the title "{title}" already exists for this task.', 'danger')
            return redirect(url_for('step_new', task_id=task_id))

        if task.start_date and task.due_date:
            try:
                task_s = datetime.strptime(task.start_date, '%Y-%m-%d').date()
                task_d = datetime.strptime(task.due_date, '%Y-%m-%d').date()
                if start_datetime:
                    st_s = datetime.fromisoformat(start_datetime).date()
                    if st_s < task_s or st_s > task_d:
                        flash(f'Subtask start date must be within task timeline ({task.start_date} to {task.due_date}).', 'warning')
                        return redirect(url_for('step_new', task_id=task_id))
                if due_datetime:
                    st_d = datetime.fromisoformat(due_datetime).date()
                    if st_d < task_s or st_d > task_d:
                        flash(f'Subtask due date must be within task timeline ({task.start_date} to {task.due_date}).', 'warning')
                        return redirect(url_for('step_new', task_id=task_id))
            except Exception as e:
                pass

        # Get max order
        steps = TaskStep.filter(task_id=task_id)
        max_order = max([s.order for s in steps]) if steps else 0

        step = TaskStep(
            task_id=task_id,
            title=title,
            description=description,
            order=max_order + 1,
            assignee_id=assignee_id if assignee_id else None,
            status='not_started',
            spoc_name=spoc_name,
            spoc_email=spoc_email,
            spoc_custom_message=spoc_custom_message,
            estimated_tat_days=int(estimated_tat_days) if estimated_tat_days else None,
            start_datetime=start_datetime if start_datetime else None,
            due_datetime=due_datetime if due_datetime else None,
            notify_on_start=notify_on_start
        )
        step.save()

        log_audit('create', 'subtask', step.id, f'Created subtask: {title}')
        flash('Subtask created successfully', 'success')
        return redirect(url_for('task_detail', task_id=task_id))

    users = User.all()
    spoc_names, spoc_emails = get_unique_spocs()
    return render_template('simple_subtask_form.html',
                         user=user,
                         task=task,
                         users=users,
                         spoc_names=spoc_names,
                         spoc_emails=spoc_emails)


@app.route('/subtasks/<step_id>/edit', methods=['GET', 'POST'])
@login_required
def step_edit(step_id):
    """Edit a subtask."""
    user = get_current_user()
    step = TaskStep.get(step_id)

    if not step:
        flash('Subtask not found', 'danger')
        return redirect(url_for('task_list'))

    task = Task.get(step.task_id)

    if request.method == 'POST':
        old_status = step.status
        step._data['title'] = request.form.get('title', '').strip()
        step._data['description'] = request.form.get('description', '').strip()
        step._data['assignee_id'] = request.form.get('assignee_id') or None
        step._data['status'] = request.form.get('status', 'not_started')
        step._data['spoc_name'] = request.form.get('spoc_name', '').strip()
        step._data['spoc_email'] = request.form.get('spoc_email', '').strip()
        step._data['spoc_custom_message'] = request.form.get('spoc_custom_message', '').strip()
        
        est_days = request.form.get('estimated_tat_days')
        step._data['estimated_tat_days'] = int(est_days) if est_days else None
        step._data['start_datetime'] = request.form.get('start_datetime', '') or None
        step._data['due_datetime'] = request.form.get('due_datetime', '') or None
        step._data['notify_on_start'] = request.form.get('notify_on_start') == 'yes'

        if task.start_date and task.due_date:
            try:
                task_s = datetime.strptime(task.start_date, '%Y-%m-%d').date()
                task_d = datetime.strptime(task.due_date, '%Y-%m-%d').date()
                if step._data['start_datetime']:
                    st_s = datetime.fromisoformat(step._data['start_datetime']).date()
                    if st_s < task_s or st_s > task_d:
                        flash(f'Subtask start date must be within task timeline ({task.start_date} to {task.due_date}).', 'warning')
                        return redirect(url_for('step_edit', step_id=step_id))
                if step._data['due_datetime']:
                    st_d = datetime.fromisoformat(step._data['due_datetime']).date()
                    if st_d < task_s or st_d > task_d:
                        flash(f'Subtask due date must be within task timeline ({task.start_date} to {task.due_date}).', 'warning')
                        return redirect(url_for('step_edit', step_id=step_id))
            except Exception as e:
                pass

        if step._data['status'] == 'completed' and not step.completed_at:
            step._data['completed_at'] = datetime.now().isoformat()

        # Check if we should notify SPOC on start
        if step._data['status'] == 'in_progress' and old_status != 'in_progress' and getattr(step, 'notify_on_start', False):
            if step.spoc_email:
                subject = f"Subtask Started: {step.title}"
                if step.spoc_custom_message:
                    body = step.spoc_custom_message
                else:
                    body = f"Hello {step.spoc_name or 'Team'},\n\nI'm writing to inform you that the subtask '{step.title}' has just started.\n\nBest regards."
                
                success, log = EmailService.send_email(
                    recipient=step.spoc_email,
                    subject=subject,
                    body=body
                )
                if success:
                    log_audit('email', 'subtask', step.id, f'Sent start email to SPOC {step.spoc_email}')
                    flash(f'Start notification sent to SPOC ({step.spoc_email}).', 'success')
                else:
                    log_audit('email_error', 'subtask', step.id, f'Failed to send start email: {log}')
                    flash(f'Failed to send start notification to SPOC. Check logs.', 'danger')

        step.save()
        log_audit('update', 'subtask', step.id, f'Updated subtask: {step.title}')
        flash('Subtask updated successfully', 'success')
        return redirect(url_for('task_detail', task_id=task.id))

    users = User.all()
    spoc_names, spoc_emails = get_unique_spocs()
    return render_template('simple_subtask_form.html',
                         user=user,
                         task=task,
                         step=step,
                         users=users,
                         spoc_names=spoc_names,
                         spoc_emails=spoc_emails)


@app.route('/subtasks/<step_id>/delete', methods=['POST'])
@login_required
def step_delete(step_id):
    """Delete a subtask."""
    step = TaskStep.get(step_id)

    if not step:
        flash('Subtask not found', 'danger')
        return redirect(url_for('task_list'))

    task_id = step.task_id
    title = step.title
    step.delete()

    log_audit('delete', 'subtask', step_id, f'Deleted subtask: {title}')
    flash(f'Subtask "{title}" deleted successfully', 'success')
    return redirect(url_for('task_detail', task_id=task_id))


@app.route('/subtasks/<step_id>/complete', methods=['POST'])
@login_required
def step_complete(step_id):
    """Quickly mark a subtask as complete."""
    step = TaskStep.get(step_id)

    if not step:
        flash('Subtask not found', 'danger')
        return redirect(url_for('task_list'))

    step._data['status'] = 'completed'
    step._data['completed_at'] = datetime.now().isoformat()
    step.save()
    
    log_audit('update', 'subtask', step.id, f'Marked subtask as complete: {step.title}')
    flash('Subtask marked as complete!', 'success')

    return redirect(url_for('task_detail', task_id=step.task_id))


@app.route('/subtasks/<step_id>/send_custom_email', methods=['POST'])
@login_required
def step_send_custom_email(step_id):
    """Send a custom email regarding a subtask."""
    step = TaskStep.get(step_id)
    if not step:
        flash('Subtask not found', 'danger')
        return redirect(url_for('task_list'))
        
    recipient = request.form.get('recipient', '').strip()
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    
    if not recipient or not subject or not body:
        flash('Recipient, Subject, and Body are required.', 'danger')
        return redirect(url_for('task_detail', task_id=step.task_id))
        
    # Send email using EmailService
    success, log = EmailService.send_email(
        recipient=recipient,
        subject=subject,
        body=body
    )
    
    if success:
        log_audit('email_sent', 'subtask', step.id, f'Custom email sent to {recipient} with subject "{subject}"')
        flash(f'Email sent successfully to {recipient} for subtask!', 'success')
    else:
        flash(f'Failed to send email to {recipient}. Check logs.', 'danger')
        
    return redirect(url_for('task_detail', task_id=step.task_id))


# ============================================================================
# Reporting Routes
# ============================================================================

@app.route('/reports/export')
@login_required
def export_summary():
    """Export a summary of all tasks and steps to Excel."""
    import pandas as pd
    import io
    from flask import send_file
    
    tasks = Task.all()
    steps = TaskStep.all()
    users = {u.id: u for u in User.all()}
    
    # Create DataFrames
    task_data = []
    for t in tasks:
        owner = users.get(t.owner_id)
        task_data.append({
            'ID': t.id,
            'Title': t.title,
            'Description': t.description,
            'Status': t.status,
            'Priority': t.priority,
            'Owner': owner.full_name if owner else 'Unassigned',
            'Progress %': t.progress_percent,
            'Created At': t.created_at,
            'Due Date': t.due_date,
            'Completed At': t.completed_at
        })
        
    step_data = []
    for s in steps:
        assignee = users.get(s.assignee_id)
        task = next((t for t in tasks if t.id == s.task_id), None)
        step_data.append({
            'Task ID': s.task_id,
            'Task Title': task.title if task else 'Unknown',
            'Step Order': s.order,
            'Title': s.title,
            'Status': s.status,
            'Assignee': assignee.full_name if assignee else 'Unassigned',
            'Estimated Days': s.estimated_tat_days,
            'Due Date': s.due_datetime,
            'Completed At': s.completed_at
        })
        
    df_tasks = pd.DataFrame(task_data)
    df_steps = pd.DataFrame(step_data)
    
    # Save to memory buffer
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_tasks.to_excel(writer, sheet_name='Tasks', index=False)
        df_steps.to_excel(writer, sheet_name='Steps', index=False)
        
        # Auto-adjust columns width
        for sheetname in writer.sheets:
            worksheet = writer.sheets[sheetname]
            worksheet.autofit()
            
    buffer.seek(0)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'Project_Summary_{timestamp}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ============================================================================
# API Routes (for JavaScript interactions)
# ============================================================================

@app.route('/api/tasks')
@login_required
def api_tasks():
    """Get all tasks as JSON."""
    tasks = Task.all()
    return jsonify([t.to_dict() for t in tasks])


@app.route('/api/tasks/<task_id>/steps')
@login_required
def api_task_steps(task_id):
    """Get steps for a task as JSON."""
    steps = TaskStep.filter(task_id=task_id)
    return jsonify([s.to_dict() for s in sorted(steps, key=lambda x: x.order or 0)])


@app.route('/calendar')
@login_required
def calendar():
    """Calendar view."""
    user = get_current_user()
    return render_template('simple_calendar.html', user=user)


@app.route('/api/tasks_calendar')
@login_required
def api_tasks_calendar():
    """Get tasks formatted for FullCalendar."""
    user = get_current_user()
    all_tasks = Task.all()
    my_tasks = [t for t in all_tasks if t.owner_id == user.id]
    
    # Get all subtasks to filter for my_tasks
    all_steps = TaskStep.all()
    
    events = []
    for t in my_tasks:
        if t.due_date:
            events.append({
                'id': f"task_{t.id}",
                'title': f"Task: {t.title}",
                'start': t.due_date, # Fallback to due date as start if no start_date
                'url': url_for('task_detail', task_id=t.id),
                'backgroundColor': '#198754' if t.status == 'completed' else ('#dc3545' if t.priority == 'high' or t.priority == 'critical' else '#4f46e5')
            })
            
        # Add subtasks for this task
        task_steps = [s for s in all_steps if s.task_id == t.id]
        for s in task_steps:
            if s.due_datetime:
                events.append({
                    'id': f"subtask_{s.id}",
                    'title': f"Sub: {s.title}",
                    'start': s.due_datetime,
                    'url': url_for('task_detail', task_id=t.id),
                    'backgroundColor': '#20c997' if s.status == 'completed' else '#ffc107',
                    'textColor': '#000' if s.status != 'completed' else '#fff'
                })
                
    return jsonify(events)


@app.route('/api/dashboard_stats')
@login_required
def api_dashboard_stats():
    """Get real-time dashboard stats."""
    user = get_current_user()
    
    all_tasks = Task.all()
    my_tasks = [t for t in all_tasks if t.owner_id == user.id]

    all_steps = TaskStep.all()
    my_steps = [s for s in all_steps if s.assignee_id == user.id]

    task_status_counts = {}
    for task in my_tasks:
        status = task.status or 'unknown'
        task_status_counts[status] = task_status_counts.get(status, 0) + 1

    now = datetime.now()
    overdue_count = 0
    for step in my_steps:
        if step.status not in ['completed', 'cancelled'] and step.due_datetime:
            try:
                due = datetime.fromisoformat(step.due_datetime)
                if due < now:
                    overdue_count += 1
            except:
                pass

    return jsonify({
        'total_tasks': len(my_tasks),
        'total_steps': len(my_steps),
        'overdue_count': overdue_count,
        'in_progress': task_status_counts.get('in_progress', 0)
    })

# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """404 error handler."""
    return render_template('simple_error.html',
                         error_code=404,
                         error_message='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler."""
    return render_template('simple_error.html',
                         error_code=500,
                         error_message='Internal server error'), 500


# ============================================================================
# Template Filters
# ============================================================================

@app.template_filter('datetime')
def format_datetime(value):
    """Format datetime string."""
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return value


@app.template_filter('date')
def format_date(value):
    """Format date string."""
    if not value:
        return ''
    try:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value)
        else:
            dt = value
        return dt.strftime('%Y-%m-%d')
    except:
        return value


@app.template_filter('status_badge')
def status_badge(status):
    """Get Bootstrap badge class for status."""
    badges = {
        'draft': 'secondary',
        'not_started': 'info',
        'in_progress': 'primary',
        'on_hold': 'warning',
        'completed': 'success',
        'cancelled': 'danger'
    }
    return badges.get(status, 'secondary')


@app.template_filter('priority_badge')
def priority_badge(priority):
    """Get Bootstrap badge class for priority."""
    badges = {
        'low': 'success',
        'medium': 'warning',
        'high': 'danger',
        'critical': 'danger'
    }
    return badges.get(priority, 'secondary')


# ============================================================================
# Main
# ============================================================================




# ============================================================================
# User Management Routes
# ============================================================================

@app.route('/users')
@login_required
def user_list():
    """List all users."""
    user = get_current_user()
    users = User.all()
    # Sort users by username
    users = sorted(users, key=lambda u: u.username.lower())
    return render_template('simple_user_list.html', user=user, users=users)

@app.route('/users/new', methods=['GET', 'POST'])
@login_required
def user_new():
    """Create a new user."""
    user = get_current_user()
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        is_active = request.form.get('is_active') == 'on'
        is_superuser = request.form.get('is_superuser') == 'on'
        
        if not username or not email or not password:
            flash('Username, Email, and Password are required', 'danger')
            return redirect(url_for('user_new'))
            
        # Check if username exists
        for u in User.all():
            if u.username == username:
                flash(f'Username "{username}" is already taken.', 'danger')
                return redirect(url_for('user_new'))
            
        new_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_staff=is_superuser,
            is_superuser=is_superuser,
            role='admin' if is_superuser else 'user'
        )
        new_user.set_password(password)
        new_user.save()
        log_audit('create', 'user', new_user.id, f'Created user: {username}')
        flash(f'User "{username}" created successfully!', 'success')
        return redirect(url_for('user_list'))
        
    return render_template('simple_user_form.html', user=user, target_user=None)

@app.route('/users/<user_id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(user_id):
    """Edit an existing user."""
    user = get_current_user()
    target_user = User.get(user_id)
    if not target_user:
        flash('User not found', 'danger')
        return redirect(url_for('user_list'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        # Prevent disabling oneself
        if user_id == user.id:
            is_active = True
            is_superuser = True
        else:
            is_active = request.form.get('is_active') == 'on'
            is_superuser = request.form.get('is_superuser') == 'on'
        
        if not username or not email:
            flash('Username and Email are required', 'danger')
            return redirect(url_for('user_edit', user_id=user_id))
            
        target_user._data['username'] = username
        target_user._data['email'] = email
        target_user._data['first_name'] = first_name
        target_user._data['last_name'] = last_name
        target_user._data['is_active'] = is_active
        target_user._data['is_staff'] = is_superuser
        target_user._data['is_superuser'] = is_superuser
        target_user._data['role'] = 'admin' if is_superuser else 'user'
        
        if password:
            target_user.set_password(password)
            
        target_user.save()
        log_audit('update', 'user', target_user.id, f'Updated user: {username}')
        flash(f'User "{username}" updated successfully!', 'success')
        return redirect(url_for('user_list'))
        
    return render_template('simple_user_form.html', user=user, target_user=target_user)

@app.route('/users/<user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    """Delete a user."""
    user = get_current_user()
    if user_id == user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('user_list'))
        
    target_user = User.get(user_id)
    if not target_user:
        flash('User not found', 'danger')
        return redirect(url_for('user_list'))
        
    username = target_user.username
    target_user.delete()
    log_audit('delete', 'user', user_id, f'Deleted user: {username}')
    flash(f'User "{username}" deleted successfully', 'success')
    return redirect(url_for('user_list'))


# ============================================================================
# Audit Log Routes
# ============================================================================

@app.route('/audit-log')
@login_required
def audit_log():
    """View global audit log."""
    user = get_current_user()
    logs = AuditLog.all()
    # Sort newest first
    logs = sorted(logs, key=lambda l: l.created_at or '', reverse=True)
    
    users = {u.id: u for u in User.all()}
    
    return render_template('simple_audit_log.html', user=user, logs=logs, users=users)

if __name__ == '__main__':
    print("="*60)
    print("Project Scheduler - Local Application")
    print("Excel-based storage (no database required)")
    print("="*60)
    print()
    print("Starting server at http://127.0.0.1:8000")
    print("Press CTRL+C to stop")
    print()

    app.run(debug=True, port=8000)
