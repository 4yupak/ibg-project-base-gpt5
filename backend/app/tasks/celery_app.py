"""
Celery application configuration for background tasks.
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


# Create Celery app
celery_app = Celery(
    "propbase",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.price_tasks",
        "app.tasks.notification_tasks",
        "app.tasks.sync_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    
    # Task routing
    task_routes={
        "app.tasks.price_tasks.*": {"queue": "price_processing"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
        "app.tasks.sync_tasks.*": {"queue": "sync"},
    },
    
    # Beat schedule for periodic tasks
    beat_schedule={
        # Update exchange rates daily at 00:00 UTC
        "update-exchange-rates": {
            "task": "app.tasks.sync_tasks.update_exchange_rates",
            "schedule": crontab(hour=0, minute=0),
        },
        # Check for price updates from Google Sheets - every 6 hours
        "check-gsheets-updates": {
            "task": "app.tasks.price_tasks.check_gsheets_updates",
            "schedule": crontab(hour="*/6", minute=0),
        },
        # Send weekly price request reminders - Monday 09:00 UTC
        "send-price-reminders": {
            "task": "app.tasks.notification_tasks.send_price_update_reminders",
            "schedule": crontab(day_of_week=1, hour=9, minute=0),
        },
        # Clean up old logs - daily at 03:00 UTC
        "cleanup-old-logs": {
            "task": "app.tasks.sync_tasks.cleanup_old_logs",
            "schedule": crontab(hour=3, minute=0),
        },
        # Recalculate project statistics - every hour
        "recalculate-project-stats": {
            "task": "app.tasks.sync_tasks.recalculate_project_statistics",
            "schedule": crontab(minute=0),
        },
        # Sync with amoCRM - every 15 minutes
        "sync-amocrm": {
            "task": "app.tasks.sync_tasks.sync_amocrm_leads",
            "schedule": crontab(minute="*/15"),
        },
    },
)


# Task base class with error handling
class BaseTask(celery_app.Task):
    """Base task with automatic retry and error logging."""
    
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600  # 10 minutes
    retry_jitter = True
    max_retries = 3
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failure."""
        # TODO: Send alert to Telegram/email
        print(f"Task {self.name}[{task_id}] failed: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)


celery_app.Task = BaseTask
