import logging
from celery import shared_task

logger = logging.getLogger('apps.fraud')


@shared_task
def run_fraud_detection_task():
    from .services import run_all_detections
    return run_all_detections()
