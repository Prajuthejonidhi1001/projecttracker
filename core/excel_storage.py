"""
Excel-based storage backend for Project Scheduler.
Replaces database with local Excel files for office environments with restrictions.
"""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
import threading


class ExcelStorage:
    """Thread-safe Excel file storage manager."""

    _lock = threading.Lock()
    _instances = {}

    def __init__(self, storage_dir: str = "excel_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

        # Define all Excel files for different models
        self.files = {
            'users': self.storage_dir / 'users.xlsx',
            'tasks': self.storage_dir / 'tasks.xlsx',
            'task_steps': self.storage_dir / 'task_steps.xlsx',
            'task_comments': self.storage_dir / 'task_comments.xlsx',
            'task_attachments': self.storage_dir / 'task_attachments.xlsx',
            'step_dependencies': self.storage_dir / 'step_dependencies.xlsx',
            'reminders': self.storage_dir / 'reminders.xlsx',
            'scheduler_runs': self.storage_dir / 'scheduler_runs.xlsx',
            'scheduler_heartbeats': self.storage_dir / 'scheduler_heartbeats.xlsx',
            'holidays': self.storage_dir / 'holidays.xlsx',
            'app_settings': self.storage_dir / 'app_settings.xlsx',
            'email_logs': self.storage_dir / 'email_logs.xlsx',
            'audit_logs': self.storage_dir / 'audit_logs.xlsx',
            'projects': self.storage_dir / 'projects.xlsx',
        }

        self._initialize_files()

    def _initialize_files(self):
        """Initialize Excel files with proper schemas if they don't exist."""
        self.schemas = {
            'users': ['id', 'username', 'email', 'password', 'first_name', 'last_name',
                     'is_active', 'is_staff', 'is_superuser', 'date_joined', 'last_login',
                     'role', 'created_at', 'updated_at'],

            'tasks': ['id', 'title', 'description', 'owner_id', 'created_by_id', 'project_id',
                     'status', 'priority', 'spoc_name', 'spoc_email', 'spoc_dept', 'progress_percent', 'start_date', 'due_date',
                     'completed_at', 'archived_at', 'notification_recipients',
                     'enable_reminders', 'created_at', 'updated_at'],

            'task_steps': ['id', 'task_id', 'title', 'description', 'spoc_name', 'spoc_email', 'spoc_custom_message', 'order', 'assignee_id',
                          'status', 'start_datetime', 'due_datetime', 'completed_at',
                          'estimated_tat_days', 'actual_tat_days', 'is_overdue',
                          'enable_reminders', 'notify_on_start', 'reminder_recipients', 'reminder_days_before',
                          'reminder_time', 'created_at', 'updated_at'],

            'task_comments': ['id', 'task_id', 'author_id', 'content', 'created_at', 'updated_at'],
            
            'task_attachments': ['id', 'task_id', 'uploader_id', 'filename', 'file_path', 'created_at', 'updated_at'],

            'step_dependencies': ['id', 'step_id', 'depends_on_step_id', 'created_at'],

            'reminders': ['id', 'step_id', 'reminder_type', 'recipient_email',
                         'scheduled_at', 'sent_at', 'status', 'retry_count',
                         'last_error', 'created_at', 'updated_at'],

            'scheduler_runs': ['id', 'started_at', 'completed_at', 'status', 'duration_seconds',
                              'reminders_generated', 'reminders_sent', 'reminders_failed',
                              'error_message', 'worker_name', 'created_at'],

            'scheduler_heartbeats': ['id', 'worker_name', 'pid', 'last_heartbeat', 'created_at'],

            'holidays': ['id', 'date', 'name', 'is_recurring', 'created_at', 'updated_at'],

            'app_settings': ['id', 'key', 'value', 'description', 'created_at', 'updated_at'],

            'email_logs': ['id', 'recipient', 'subject', 'body', 'sent_at',
                          'status', 'error_message', 'created_at'],

            'audit_logs': ['id', 'user_id', 'action', 'entity_type', 'entity_id',
                          'description', 'ip_address', 'user_agent', 'created_at'],

            'projects': ['id', 'name', 'description', 'owner_id', 'status',
                        'start_date', 'end_date', 'created_at', 'updated_at'],
        }

        for model_name, columns in self.schemas.items():
            file_path = self.files[model_name]
            if not file_path.exists():
                df = pd.DataFrame(columns=columns)
                df.to_excel(file_path, index=False, engine='openpyxl')

    def _read_excel(self, model_name: str) -> pd.DataFrame:
        """Read data from Excel file."""
        file_path = self.files[model_name]
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
            
            # Ensure all columns from schema exist
            if model_name in self.schemas:
                for col in self.schemas[model_name]:
                    if col not in df.columns:
                        df[col] = None
                        
            # Convert NaN to None for better handling
            df = df.where(pd.notnull(df), None)
            return df
        except Exception as e:
            print(f"Error reading {model_name}: {e}")
            return pd.DataFrame()

    def _write_excel(self, model_name: str, df: pd.DataFrame):
        """Write data to Excel file."""
        file_path = self.files[model_name]
        with self._lock:
            try:
                df.to_excel(file_path, index=False, engine='openpyxl')
            except Exception as e:
                print(f"Error writing {model_name}: {e}")
                raise

    def create(self, model_name: str, data: Dict[str, Any]) -> str:
        """Create a new record and return its ID."""
        df = self._read_excel(model_name)

        # Generate UUID if not provided
        if 'id' not in data or not data['id']:
            data['id'] = str(uuid.uuid4())

        # Add timestamps
        now = datetime.now().isoformat()
        if 'created_at' not in data:
            data['created_at'] = now
        if 'updated_at' not in data:
            data['updated_at'] = now

        # Append new row
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)

        self._write_excel(model_name, df)
        return data['id']

    def get(self, model_name: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID."""
        df = self._read_excel(model_name)
        result = df[df['id'] == record_id]

        if result.empty:
            return None

        return result.iloc[0].to_dict()

    def filter(self, model_name: str, **filters) -> List[Dict[str, Any]]:
        """Filter records based on criteria."""
        df = self._read_excel(model_name)

        for key, value in filters.items():
            if value is not None:
                df = df[df[key] == value]

        return df.to_dict('records')

    def all(self, model_name: str) -> List[Dict[str, Any]]:
        """Get all records."""
        df = self._read_excel(model_name)
        return df.to_dict('records')

    def update(self, model_name: str, record_id: str, data: Dict[str, Any]) -> bool:
        """Update an existing record."""
        df = self._read_excel(model_name)

        mask = df['id'] == record_id
        if not mask.any():
            return False

        # Update timestamp
        data['updated_at'] = datetime.now().isoformat()

        # Update fields
        for key, value in data.items():
            if key in df.columns:
                df.loc[mask, key] = value

        self._write_excel(model_name, df)
        return True

    def delete(self, model_name: str, record_id: str) -> bool:
        """Delete a record by ID."""
        df = self._read_excel(model_name)

        initial_len = len(df)
        df = df[df['id'] != record_id]

        if len(df) < initial_len:
            self._write_excel(model_name, df)
            return True

        return False

    def count(self, model_name: str, **filters) -> int:
        """Count records matching filters."""
        return len(self.filter(model_name, **filters))

    def exists(self, model_name: str, **filters) -> bool:
        """Check if any record matches filters."""
        return self.count(model_name, **filters) > 0

    def bulk_create(self, model_name: str, records: List[Dict[str, Any]]) -> List[str]:
        """Create multiple records at once."""
        ids = []
        df = self._read_excel(model_name)

        now = datetime.now().isoformat()
        new_rows = []

        for data in records:
            if 'id' not in data or not data['id']:
                data['id'] = str(uuid.uuid4())

            if 'created_at' not in data:
                data['created_at'] = now
            if 'updated_at' not in data:
                data['updated_at'] = now

            new_rows.append(data)
            ids.append(data['id'])

        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)

        self._write_excel(model_name, df)
        return ids

    def clear_all(self, model_name: str):
        """Clear all records from a model (useful for testing)."""
        df = self._read_excel(model_name)
        empty_df = pd.DataFrame(columns=df.columns)
        self._write_excel(model_name, empty_df)

    @classmethod
    def get_instance(cls, storage_dir: str = "excel_data") -> 'ExcelStorage':
        """Get or create singleton instance."""
        if storage_dir not in cls._instances:
            cls._instances[storage_dir] = cls(storage_dir)
        return cls._instances[storage_dir]


# Global storage instance
storage = ExcelStorage.get_instance()
