"""
Setup script for local Excel-based Project Scheduler.
Run this to initialize the application for local use without database.
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from core.excel_storage import storage
from core.excel_models import User, Task, TaskStep, Project


def create_demo_data():
    """Create demo data for testing."""
    print("Creating demo data...")

    # Create admin user
    admin_data = {
        'username': 'admin',
        'email': 'admin@projectscheduler.local',
        'first_name': 'Admin',
        'last_name': 'User',
        'is_active': True,
        'is_staff': True,
        'is_superuser': True,
        'role': 'admin',
        'date_joined': datetime.now().isoformat()
    }

    admin = User(**admin_data)
    admin.set_password('admin123')
    admin.save()
    print(f"[OK] Created admin user: admin / admin123")

    # Create regular user
    user_data = {
        'username': 'user1',
        'email': 'user1@projectscheduler.local',
        'first_name': 'John',
        'last_name': 'Doe',
        'is_active': True,
        'is_staff': False,
        'is_superuser': False,
        'role': 'user',
        'date_joined': datetime.now().isoformat()
    }

    user1 = User(**user_data)
    user1.set_password('user123')
    user1.save()
    print(f"[OK] Created regular user: user1 / user123")

    # Create a project
    project_data = {
        'name': 'Sample Project',
        'description': 'A sample project for demonstration',
        'owner_id': admin.id,
        'status': 'active',
        'start_date': datetime.now().date().isoformat(),
        'end_date': None
    }

    project = Project(**project_data)
    project.save()
    print(f"[OK] Created project: {project.name}")

    # Create sample tasks
    task1_data = {
        'title': 'Setup Development Environment',
        'description': 'Install and configure all necessary tools',
        'owner_id': admin.id,
        'created_by_id': admin.id,
        'project_id': project.id,
        'status': 'in_progress',
        'priority': 'high',
        'progress_percent': 50,
        'start_date': datetime.now().date().isoformat(),
        'enable_reminders': True
    }

    task1 = Task(**task1_data)
    task1.save()
    print(f"[OK] Created task: {task1.title}")

    # Create steps for task 1
    steps_data = [
        {
            'task_id': task1.id,
            'title': 'Install Python',
            'description': 'Install Python 3.10 or higher',
            'order': 1,
            'assignee_id': user1.id,
            'status': 'completed',
            'estimated_tat_days': 1,
            'completed_at': datetime.now().isoformat()
        },
        {
            'task_id': task1.id,
            'title': 'Install Dependencies',
            'description': 'Run pip install -r requirements.txt',
            'order': 2,
            'assignee_id': user1.id,
            'status': 'in_progress',
            'estimated_tat_days': 1
        },
        {
            'task_id': task1.id,
            'title': 'Configure Environment',
            'description': 'Setup .env file with necessary configurations',
            'order': 3,
            'assignee_id': admin.id,
            'status': 'not_started',
            'estimated_tat_days': 1
        }
    ]

    for step_data in steps_data:
        step = TaskStep(**step_data)
        step.save()
        print(f"  [OK] Created step: {step.title}")

    # Create another task
    task2_data = {
        'title': 'Documentation Review',
        'description': 'Review and update project documentation',
        'owner_id': user1.id,
        'created_by_id': admin.id,
        'project_id': project.id,
        'status': 'not_started',
        'priority': 'medium',
        'progress_percent': 0,
        'start_date': datetime.now().date().isoformat(),
        'enable_reminders': False
    }

    task2 = Task(**task2_data)
    task2.save()
    print(f"[OK] Created task: {task2.title}")

    print("\n[SUCCESS] Demo data created successfully!")
    print("\nYou can now login with:")
    print("  Admin: admin / admin123")
    print("  User:  user1 / user123")


def setup_environment():
    """Setup environment and directories."""
    print("Setting up local environment...")

    # Create necessary directories
    directories = [
        BASE_DIR / 'excel_data',
        BASE_DIR / 'logs',
        BASE_DIR / 'static',
        BASE_DIR / 'staticfiles'
    ]

    for directory in directories:
        directory.mkdir(exist_ok=True)
        print(f"[OK] Created directory: {directory.name}")

    # Create .env file if it doesn't exist
    env_file = BASE_DIR / '.env'
    if not env_file.exists():
        env_content = """# Project Scheduler Environment Variables

# Django settings
SECRET_KEY=django-insecure-local-dev-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Time zone
TIME_ZONE=Asia/Kolkata

# Excel storage (no database needed)
USE_EXCEL_STORAGE=True

# Email settings (console backend for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=Project Scheduler <noreply@projectscheduler.local>

# Scheduler settings
SCHEDULER_INTERVAL_SECONDS=60
SCHEDULER_HEARTBEAT_TIMEOUT_SECONDS=300

# Business calendar mode
BUSINESS_CALENDAR_MODE=calendar_days

# Reminder defaults
DEFAULT_REMINDER_TIME=09:00
DEFAULT_REMINDER_DAYS=1

# SMTP Settings for auto-triggering emails
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_USE_TLS=True
"""
        env_file.write_text(env_content)
        print(f"[OK] Created .env file")
    else:
        print(f"[OK] .env file already exists")

    print("\n[SUCCESS] Environment setup complete!")


def check_dependencies():
    """Check if all required packages are installed."""
    print("Checking dependencies...")

    required_packages = {
        'flask': 'Flask',
        'pandas': 'pandas',
        'openpyxl': 'openpyxl',
        'dotenv': 'python-dotenv'
    }

    missing = []
    for package, pip_name in required_packages.items():
        try:
            __import__(package)
            print(f"[OK] {pip_name} installed")
        except ImportError:
            missing.append(pip_name)
            print(f"[X] {pip_name} NOT installed")

    if missing:
        print(f"\n[WARNING] Missing packages: {', '.join(missing)}")
        print("\nInstall them with:")
        print(f"  pip install {' '.join(missing)}")
        return False

    print("\n[SUCCESS] All dependencies installed!")
    return True


def main():
    """Main setup function."""
    print("="*60)
    print("Project Scheduler - Local Setup")
    print("Excel-based storage (no database required)")
    print("="*60)
    print()

    # Check dependencies
    if not check_dependencies():
        print("\n[ERROR] Please install missing dependencies first:")
        print("   pip install -r requirements.txt")
        return

    print()

    # Setup environment
    setup_environment()
    print()

    # Ask about demo data
    response = input("\nCreate demo data? (y/n): ").lower().strip()
    if response == 'y':
        create_demo_data()

    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Start the application:")
    print("   python run_local.py")
    print("\n2. Open your browser:")
    print("   http://127.0.0.1:8000")
    print("\n3. Login with demo credentials (if created):")
    print("   admin / admin123")
    print("="*60)


if __name__ == '__main__':
    main()
