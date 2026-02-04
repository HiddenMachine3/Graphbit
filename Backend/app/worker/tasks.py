from app.worker.celery_app import celery_app

@celery_app.task
def example_task():
    return "Task executed successfully"