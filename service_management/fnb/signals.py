from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserLiveStatus
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=UserLiveStatus)
def signal_wss(sender, instance, created, **kwargs):
    logger.info("WSS_SIGNAL: %s is now %s", instance.user.id, instance.current_state)
