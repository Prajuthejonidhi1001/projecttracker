"""
Excel-based model classes that mimic Django ORM behavior.
These replace Django models for office environments without database access.
"""
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Union
from .excel_storage import storage


class ExcelModel:
    """Base class for Excel-backed models."""

    _model_name = None

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', None)
        self.created_at = kwargs.get('created_at', None)
        self.updated_at = kwargs.get('updated_at', None)
        self._data = kwargs

    def save(self):
        """Save the model to Excel."""
        if self.id:
            # Update existing
            storage.update(self._model_name, self.id, self._data)
        else:
            # Create new
            self.id = storage.create(self._model_name, self._data)
            self._data['id'] = self.id
        return self

    def delete(self):
        """Delete the model from Excel."""
        if self.id:
            return storage.delete(self._model_name, self.id)
        return False

    @classmethod
    def get(cls, record_id: str):
        """Get a single record by ID."""
        data = storage.get(cls._model_name, record_id)
        if data:
            return cls(**data)
        return None

    @classmethod
    def filter(cls, **filters):
        """Filter records."""
        records = storage.filter(cls._model_name, **filters)
        return [cls(**record) for record in records]

    @classmethod
    def all(cls):
        """Get all records."""
        records = storage.all(cls._model_name)
        return [cls(**record) for record in records]

    @classmethod
    def count(cls, **filters):
        """Count records."""
        return storage.count(cls._model_name, **filters)

    @classmethod
    def exists(cls, **filters):
        """Check if records exist."""
        return storage.exists(cls._model_name, **filters)

    def to_dict(self):
        """Convert model to dictionary."""
        return self._data.copy()

    def __getattr__(self, name):
        """Allow attribute-style access to data."""
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return self._data.get(name)

    def __setattr__(self, name, value):
        """Allow attribute-style setting of data."""
        if name.startswith('_') or name in ['id', 'created_at', 'updated_at']:
            super().__setattr__(name, value)
        else:
            if not hasattr(self, '_data'):
                super().__setattr__('_data', {})
            self._data[name] = value


class User(ExcelModel):
    """User model."""
    _model_name = 'users'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.username = kwargs.get('username', '')
        self.email = kwargs.get('email', '')
        self.password = kwargs.get('password', '')
        self.first_name = kwargs.get('first_name', '')
        self.last_name = kwargs.get('last_name', '')
        self.is_active = kwargs.get('is_active', True)
        self.is_staff = kwargs.get('is_staff', False)
        self.is_superuser = kwargs.get('is_superuser', False)
        self.role = kwargs.get('role', 'user')
        self.date_joined = kwargs.get('date_joined', datetime.now().isoformat())
        self.last_login = kwargs.get('last_login', None)

    def set_password(self, raw_password):
        """Set password with secure hashing."""
        import hashlib
        import os
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', raw_password.encode('utf-8'), salt, 100000)
        self._data['password'] = salt.hex() + key.hex()
        self.password = self._data['password']

    def check_password(self, raw_password):
        """Check password."""
        import hashlib
        if not self.password or len(self.password) < 64:
            return False
        salt = bytes.fromhex(self.password[:64])
        stored_key = self.password[64:]
        key = hashlib.pbkdf2_hmac('sha256', raw_password.encode('utf-8'), salt, 100000)
        return key.hex() == stored_key

    @property
    def full_name(self):
        """Get full name."""
        return f"{self.first_name} {self.last_name}".strip() or self.username


class Task(ExcelModel):
    """Task model."""
    _model_name = 'tasks'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = kwargs.get('title', '')
        self.description = kwargs.get('description', '')
        self.owner_id = kwargs.get('owner_id', None)
        self.created_by_id = kwargs.get('created_by_id', None)
        self.project_id = kwargs.get('project_id', None)
        self.status = kwargs.get('status', 'draft')
        self.priority = kwargs.get('priority', 'medium')
        self.spoc_name = kwargs.get('spoc_name', '')
        self.spoc_email = kwargs.get('spoc_email', '')
        self.spoc_dept = kwargs.get('spoc_dept', '')
        self.progress_percent = kwargs.get('progress_percent', 0)
        self.start_date = kwargs.get('start_date', None)
        self.due_date = kwargs.get('due_date', None)
        self.completed_at = kwargs.get('completed_at', None)
        self.archived_at = kwargs.get('archived_at', None)
        self.notification_recipients = kwargs.get('notification_recipients', '')
        self.enable_reminders = kwargs.get('enable_reminders', False)

    def get_steps(self):
        """Get all steps for this task."""
        return TaskStep.filter(task_id=self.id)

    @property
    def owner(self):
        """Get owner user."""
        if self.owner_id:
            return User.get(self.owner_id)
        return None
        
    @property
    def is_overdue(self):
        if not self.due_date or self.status in ['completed', 'cancelled']:
            return False
        try:
            due = datetime.fromisoformat(self.due_date)
            return due < datetime.now()
        except ValueError:
            return False

    @property
    def is_due_soon(self):
        if not self.due_date or self.status in ['completed', 'cancelled']:
            return False
        try:
            due = datetime.fromisoformat(self.due_date)
            now = datetime.now()
            return due > now and due <= (now + timedelta(days=2))
        except ValueError:
            return False


class TaskComment(ExcelModel):
    """Task comment model."""
    _model_name = 'task_comments'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.task_id = kwargs.get('task_id', None)
        self.author_id = kwargs.get('author_id', None)
        self.content = kwargs.get('content', '')

    @property
    def author(self):
        """Get author user."""
        if self.author_id:
            return User.get(self.author_id)
        return None

    @property
    def task(self):
        """Get parent task."""
        if self.task_id:
            return Task.get(self.task_id)
        return None


class TaskAttachment(ExcelModel):
    """Task attachment model."""
    _model_name = 'task_attachments'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.task_id = kwargs.get('task_id', None)
        self.uploader_id = kwargs.get('uploader_id', None)
        self.filename = kwargs.get('filename', '')
        self.file_path = kwargs.get('file_path', '')

    @property
    def uploader(self):
        """Get uploader user."""
        if self.uploader_id:
            return User.get(self.uploader_id)
        return None


class TaskStep(ExcelModel):
    """Task step model."""
    _model_name = 'task_steps'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.task_id = kwargs.get('task_id', None)
        self.title = kwargs.get('title', '')
        self.description = kwargs.get('description', '')
        self.spoc_name = kwargs.get('spoc_name', '')
        self.spoc_email = kwargs.get('spoc_email', '')
        self.spoc_custom_message = kwargs.get('spoc_custom_message', '')
        self.order = kwargs.get('order', 0)
        self.assignee_id = kwargs.get('assignee_id', None)
        self.status = kwargs.get('status', 'not_started')
        self.start_datetime = kwargs.get('start_datetime', None)
        self.due_datetime = kwargs.get('due_datetime', None)
        self.completed_at = kwargs.get('completed_at', None)
        self.estimated_tat_days = kwargs.get('estimated_tat_days', 0)
        self.actual_tat_days = kwargs.get('actual_tat_days', 0)
        self.is_overdue = kwargs.get('is_overdue', False)
        self.enable_reminders = kwargs.get('enable_reminders', False)
        self.notify_on_start = kwargs.get('notify_on_start', False)
        self.reminder_recipients = kwargs.get('reminder_recipients', '')
        self.reminder_days_before = kwargs.get('reminder_days_before', 1)
        self.reminder_time = kwargs.get('reminder_time', '09:00')

    @property
    def task(self):
        """Get parent task."""
        if self.task_id:
            return Task.get(self.task_id)
        return None

    @property
    def assignee(self):
        """Get assignee user."""
        if self.assignee_id:
            return User.get(self.assignee_id)
        return None


class StepDependency(ExcelModel):
    """Step dependency model."""
    _model_name = 'step_dependencies'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.step_id = kwargs.get('step_id', None)
        self.depends_on_step_id = kwargs.get('depends_on_step_id', None)


class Reminder(ExcelModel):
    """Reminder model."""
    _model_name = 'reminders'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.step_id = kwargs.get('step_id', None)
        self.reminder_type = kwargs.get('reminder_type', 'before_due')
        self.recipient_email = kwargs.get('recipient_email', '')
        self.scheduled_at = kwargs.get('scheduled_at', None)
        self.sent_at = kwargs.get('sent_at', None)
        self.status = kwargs.get('status', 'pending')
        self.retry_count = kwargs.get('retry_count', 0)
        self.last_error = kwargs.get('last_error', None)


class SchedulerRun(ExcelModel):
    """Scheduler run model."""
    _model_name = 'scheduler_runs'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.started_at = kwargs.get('started_at', None)
        self.completed_at = kwargs.get('completed_at', None)
        self.status = kwargs.get('status', 'running')
        self.duration_seconds = kwargs.get('duration_seconds', 0)
        self.reminders_generated = kwargs.get('reminders_generated', 0)
        self.reminders_sent = kwargs.get('reminders_sent', 0)
        self.reminders_failed = kwargs.get('reminders_failed', 0)
        self.error_message = kwargs.get('error_message', None)
        self.worker_name = kwargs.get('worker_name', 'default')


class SchedulerHeartbeat(ExcelModel):
    """Scheduler heartbeat model."""
    _model_name = 'scheduler_heartbeats'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.worker_name = kwargs.get('worker_name', 'default')
        self.pid = kwargs.get('pid', 0)
        self.last_heartbeat = kwargs.get('last_heartbeat', datetime.now().isoformat())


class Holiday(ExcelModel):
    """Holiday model."""
    _model_name = 'holidays'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.date = kwargs.get('date', None)
        self.name = kwargs.get('name', '')
        self.is_recurring = kwargs.get('is_recurring', False)


class AppSetting(ExcelModel):
    """App setting model."""
    _model_name = 'app_settings'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.key = kwargs.get('key', '')
        self.value = kwargs.get('value', '')
        self.description = kwargs.get('description', '')


class EmailLog(ExcelModel):
    """Email log model."""
    _model_name = 'email_logs'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recipient = kwargs.get('recipient', '')
        self.subject = kwargs.get('subject', '')
        self.body = kwargs.get('body', '')
        self.sent_at = kwargs.get('sent_at', None)
        self.status = kwargs.get('status', 'pending')
        self.error_message = kwargs.get('error_message', None)


class AuditLog(ExcelModel):
    """Audit log model."""
    _model_name = 'audit_logs'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.user_id = kwargs.get('user_id', None)
        self.action = kwargs.get('action', '')
        self.entity_type = kwargs.get('entity_type', '')
        self.entity_id = kwargs.get('entity_id', None)
        self.description = kwargs.get('description', '')
        self.ip_address = kwargs.get('ip_address', None)
        self.user_agent = kwargs.get('user_agent', None)


class Project(ExcelModel):
    """Project model."""
    _model_name = 'projects'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = kwargs.get('name', '')
        self.description = kwargs.get('description', '')
        self.owner_id = kwargs.get('owner_id', None)
        self.status = kwargs.get('status', 'active')
        self.start_date = kwargs.get('start_date', None)
        self.end_date = kwargs.get('end_date', None)

    def get_tasks(self):
        """Get all tasks for this project."""
        return Task.filter(project_id=self.id)
