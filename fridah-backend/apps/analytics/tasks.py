import logging
from celery import shared_task

logger = logging.getLogger('apps.analytics')


@shared_task
def recalculate_tenant_risk_scores_task():
    from .services import recalculate_all_tenant_risk_scores
    return recalculate_all_tenant_risk_scores()
