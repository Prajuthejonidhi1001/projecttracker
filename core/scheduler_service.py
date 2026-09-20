import logging
from datetime import datetime, timedelta
from .excel_models import Task, TaskStep, User, Reminder
from .email_service import EmailService

logger = logging.getLogger("scheduler_service")

class SchedulerService:
    @staticmethod
    def _has_reminder_been_sent(step_id, recipient, reminder_type):
        reminders = Reminder.filter(
            step_id=step_id, 
            recipient_email=recipient, 
            reminder_type=reminder_type,
            status='sent'
        )
        return len(reminders) > 0

    @staticmethod
    def _log_reminder(step_id, recipient, reminder_type, status='sent', error_msg=None):
        r = Reminder(
            step_id=step_id,
            reminder_type=reminder_type,
            recipient_email=recipient,
            status=status,
            scheduled_at=datetime.now().isoformat(),
            sent_at=datetime.now().isoformat() if status == 'sent' else None,
            last_error=error_msg
        )
        r.save()

    @staticmethod
    def check_and_send_reminders():
        """Check all tasks and steps, send emails if necessary."""
        logger.info("Running scheduler check for email reminders...")
        
        now = datetime.now()
        steps = TaskStep.all()
        
        for step in steps:
            if not step.enable_reminders or step.status in ['completed', 'cancelled'] or not step.due_datetime:
                continue
                
            try:
                due = datetime.fromisoformat(step.due_datetime)
            except ValueError:
                continue

            task = step.task
            if not task or task.status in ['completed', 'cancelled', 'archived']:
                continue

            assignee = step.assignee
            recipient = assignee.email if assignee and assignee.email else None
            
            if not recipient:
                continue

            # Reminder Type 1: Overdue
            if due < now:
                reminder_type = "overdue"
                if not SchedulerService._has_reminder_been_sent(step.id, recipient, reminder_type):
                    subject = f"OVERDUE: Task Step '{step.title}'"
                    body = f"Hello {assignee.first_name},\n\nYour step '{step.title}' for task '{task.title}' is OVERDUE.\nIt was due on {due.strftime('%Y-%m-%d %H:%M')}.\n\nPlease update it in the Project Scheduler."
                    
                    success, log = EmailService.send_email(recipient, subject, body)
                    SchedulerService._log_reminder(step.id, recipient, reminder_type, 'sent' if success else 'failed')

            # Reminder Type 2: Due Soon (e.g., within 24 hours)
            elif due < (now + timedelta(days=1)):
                reminder_type = "due_soon"
                if not SchedulerService._has_reminder_been_sent(step.id, recipient, reminder_type):
                    subject = f"REMINDER: Task Step '{step.title}' due soon"
                    body = f"Hello {assignee.first_name},\n\nYour step '{step.title}' for task '{task.title}' is due soon.\nIt is due on {due.strftime('%Y-%m-%d %H:%M')}.\n\nPlease update it in the Project Scheduler."
                    
                    success, log = EmailService.send_email(recipient, subject, body)
                    SchedulerService._log_reminder(step.id, recipient, reminder_type, 'sent' if success else 'failed')

        logger.info("Scheduler check completed for TaskSteps.")
        
        # Check Main Tasks for SPOC reminders
        logger.info("Checking Main Tasks for SPOC reminders...")
        tasks = Task.all()
        for task in tasks:
            if task.status in ['completed', 'cancelled', 'archived'] or not task.due_date or not task.spoc_email:
                continue
                
            try:
                due = datetime.fromisoformat(task.due_date)
            except ValueError:
                continue
                
            # If due within 24 hours and not overdue
            if due > now and due < (now + timedelta(days=1)):
                reminder_type = "task_due_soon"
                if not SchedulerService._has_reminder_been_sent(task.id, task.spoc_email, reminder_type):
                    subject = f"URGENT: Task '{task.title}' Deadline Approaching (1 Day Left)"
                    body = f"Hello {task.spoc_name or 'SPOC'},\n\nThe task '{task.title}' is due in less than 24 hours.\nIt is due on {due.strftime('%Y-%m-%d %H:%M')}.\n\nPlease ensure it is on track to be completed on time."
                    
                    success, log = EmailService.send_email(task.spoc_email, subject, body)
                    SchedulerService._log_reminder(task.id, task.spoc_email, reminder_type, 'sent' if success else 'failed')
                    
        logger.info("Scheduler check completed for all items.")
