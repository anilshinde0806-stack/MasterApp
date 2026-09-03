from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import JobCardQualityCheck
from apps.quality_check.services.quality_check_items import (
    ensure_quality_check_items,
)


@receiver(
    post_save,
    sender=JobCardQualityCheck,
)
def create_quality_check_items(
    sender,
    instance,
    created,
    **kwargs,
):
    if created:
        ensure_quality_check_items(instance)