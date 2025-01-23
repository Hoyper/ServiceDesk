from celery import Celery

celery_app = Celery(
    "tasks", broker="redis://localhost:6379/0", backend="redis://localhost:6379/0"
)

celery_app.conf.beat_schedule = {
    "check-operator-email": {
        "task": "app.services.email_service.check_operator_email",
        "schedule": 20.0,
    },
}
celery_app.conf.timezone = "UTC"
