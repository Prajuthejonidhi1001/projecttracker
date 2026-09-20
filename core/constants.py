"""Shared constants for the whole application."""
from django.db import models


class TaskStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    NOT_STARTED = "not_started", "Not Started"
    IN_PROGRESS = "in_progress", "In Progress"
    ON_HOLD = "on_hold", "On Hold"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    ARCHIVED = "archived", "Archived"


class StepStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    OVERDUE = "overdue", "Overdue"
    ON_HOLD = "on_hold", "On Hold"
    CANCELLED = "cancelled", "Cancelled"


class Priority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class TATUnit(models.TextChoices):
    HOURS = "hours", "Hours"
    DAYS = "days", "Days"
    WEEKS = "weeks", "Weeks"


class DependencyType(models.TextChoices):
    NONE = "none", "No Dependency"
    SEQUENTIAL = "sequential", "Sequential (previous step)"


class ReminderType(models.TextChoices):
    BEFORE_DUE = "before_due", "Before Due Date"
    ON_DUE = "on_due", "On Due Date"
    OVERDUE = "overdue", "Overdue"


class ReminderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class EmailLogStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"


class SchedulerStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class UserRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    MANAGER = "manager", "Manager"
    OWNER = "owner", "Owner"
    REVIEWER = "reviewer", "Reviewer"