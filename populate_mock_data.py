import os
import sys
from datetime import datetime, timedelta
import random

# Add project to path
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.excel_models import User, Task, TaskStep

def populate_data():
    print("Populating mock data...")
    admin = User.get('admin')
    if not admin:
        print("Admin user not found. Creating one...")
        admin = User(id='admin', username='admin', full_name='Admin User')
        admin.set_password('admin123')
        admin.save()
        
    admin_id = admin.id
    
    # Create Tasks
    today = datetime.now().date()
    
    tasks_data = [
        {
            'title': 'Website Redesign 2026',
            'description': 'Complete overhaul of the corporate website.',
            'status': 'in_progress',
            'priority': 'high',
            'spoc_name': 'Alice Smith',
            'spoc_email': 'alice@example.com',
            'spoc_dept': 'Marketing',
            'start_date': (today - timedelta(days=5)).isoformat(),
            'due_date': (today + timedelta(days=20)).isoformat(),
        },
        {
            'title': 'Q4 Financial Audit',
            'description': 'Year end financial review and compliance audit.',
            'status': 'not_started',
            'priority': 'critical',
            'spoc_name': 'Bob Johnson',
            'spoc_email': 'bob@example.com',
            'spoc_dept': 'Finance',
            'start_date': (today + timedelta(days=1)).isoformat(),
            'due_date': (today + timedelta(days=15)).isoformat(),
        },
        {
            'title': 'Server Migration to Cloud',
            'description': 'Move on-prem servers to GCP.',
            'status': 'in_progress',
            'priority': 'high',
            'spoc_name': 'Charlie Tech',
            'spoc_email': 'charlie@example.com',
            'spoc_dept': 'IT Ops',
            'start_date': (today - timedelta(days=10)).isoformat(),
            'due_date': (today + timedelta(days=5)).isoformat(),
        },
        {
            'title': 'Employee Onboarding Revamp',
            'description': 'Update HR materials for new hires.',
            'status': 'completed',
            'priority': 'medium',
            'spoc_name': 'Diana Prince',
            'spoc_email': 'diana@example.com',
            'spoc_dept': 'HR',
            'start_date': (today - timedelta(days=30)).isoformat(),
            'due_date': (today - timedelta(days=2)).isoformat(),
            'due_date': (today - timedelta(days=2)).isoformat(),
            'completed_at': (today - timedelta(days=2)).isoformat(),
        },
        {
            'title': 'Overdue Time Breach Example',
            'description': 'This project should show red striped bars.',
            'status': 'in_progress',
            'priority': 'high',
            'spoc_name': 'Late Larry',
            'spoc_email': 'larry@example.com',
            'spoc_dept': 'Operations',
            'start_date': (today - timedelta(days=20)).isoformat(),
            'due_date': (today - timedelta(days=5)).isoformat(),
        }
    ]
    
    for td in tasks_data:
        t = Task(
            created_by_id=admin_id,
            title=td['title'],
            description=td['description'],
            status=td['status'],
            priority=td['priority'],
            spoc_name=td['spoc_name'],
            spoc_email=td['spoc_email'],
            spoc_dept=td['spoc_dept'],
            start_date=td['start_date'],
            due_date=td['due_date'],
            completed_at=td.get('completed_at')
        )
        t.save()
        print(f"Created task: {t.title}")
        
        # Create subtasks for this task
        t_start = datetime.strptime(td['start_date'], '%Y-%m-%d')
        
        if td['title'] == 'Website Redesign 2026':
            subtasks = [
                ('Design Wireframes', 'completed', 0, 5),
                ('Frontend Development', 'in_progress', 6, 12),
                ('Backend Integration', 'not_started', 13, 20)
            ]
        elif td['title'] == 'Q4 Financial Audit':
            subtasks = [
                ('Gather Documents', 'not_started', 0, 4),
                ('Initial Review', 'not_started', 5, 10),
                ('Final Report', 'not_started', 11, 14)
            ]
        elif td['title'] == 'Server Migration to Cloud':
            subtasks = [
                ('Backup Data', 'completed', 0, 2),
                ('Provision Cloud Resources', 'completed', 3, 5),
                ('Data Transfer', 'in_progress', 6, 10),
                ('DNS Switch', 'not_started', 11, 15)
            ]
        elif td['title'] == 'Overdue Time Breach Example':
            subtasks = [
                ('Initial Planning', 'completed', 0, 5),
                ('Stalled Execution', 'in_progress', 6, 12),
                ('Final Delivery', 'not_started', 13, 15)
            ]
        else:
            subtasks = [
                ('Draft materials', 'completed', 0, 10),
                ('Review & Publish', 'completed', 11, 28)
            ]
            
        for idx, st in enumerate(subtasks):
            step = TaskStep(
                task_id=t.id,
                title=st[0],
                description=f"Description for {st[0]}",
                status=st[1],
                order=idx+1,
                spoc_name=td['spoc_name'],
                spoc_email=td['spoc_email'],
                start_datetime=(t_start + timedelta(days=st[2])).isoformat() + "T09:00",
                due_datetime=(t_start + timedelta(days=st[3])).isoformat() + "T17:00",
            )
            step.save()
            
    print("Mock data populated successfully!")

if __name__ == '__main__':
    populate_data()
