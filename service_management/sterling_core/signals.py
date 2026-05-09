import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import SterlingUser, Unit, Membership
import redis

logger = logging.getLogger(__name__)

def get_redis_client():
    return redis.Redis(host='redis', port=6379, decode_responses=True)

@receiver(post_save, sender=Unit)
def update_unit_cache(sender, instance, created, **kwargs):
    try:
        r = get_redis_client()
        r.hset(f"cache:unit:{instance.id}", mapping={
            "org_id": str(instance.organization.id),
            "vertical": "SCHOOL"
        })
    except Exception as e:
        logger.error("Failed to update unit cache: %s", e)

@receiver(post_delete, sender=Unit)
def delete_unit_cache(sender, instance, **kwargs):
    try:
        r = get_redis_client()
        r.delete(f"cache:unit:{instance.id}")
    except Exception as e:
        logger.error("Failed to delete unit cache: %s", e)

@receiver(post_save, sender=SterlingUser)
def update_user_rfid_cache(sender, instance, created, **kwargs):
    if not instance.hashed_rfid:
        return
    try:
        r = get_redis_client()
        primary_membership = instance.memberships.filter(is_primary=True).first()
        primary_unit_id = str(primary_membership.unit.id) if primary_membership else ""
        r.hset(f"cache:rfid:{instance.hashed_rfid}", mapping={
            "user_id": str(instance.id),
            "primary_unit_id": primary_unit_id
        })
    except Exception as e:
        logger.error("Failed to update user RFID cache: %s", e)

@receiver(post_delete, sender=SterlingUser)
def delete_user_rfid_cache(sender, instance, **kwargs):
    if not instance.hashed_rfid:
        return
    try:
        r = get_redis_client()
        r.delete(f"cache:rfid:{instance.hashed_rfid}")
    except Exception as e:
        logger.error("Failed to delete user RFID cache: %s", e)

@receiver(post_save, sender=Membership)
def update_membership_cache(sender, instance, created, **kwargs):
    if not instance.user.hashed_rfid:
        return
    try:
        r = get_redis_client()
        primary_membership = instance.user.memberships.filter(is_primary=True).first()
        primary_unit_id = str(primary_membership.unit.id) if primary_membership else ""
        r.hset(f"cache:rfid:{instance.user.hashed_rfid}", mapping={
            "user_id": str(instance.user.id),
            "primary_unit_id": primary_unit_id
        })
    except Exception as e:
        logger.error("Failed to update membership cache: %s", e)

@receiver(post_delete, sender=Membership)
def delete_membership_cache(sender, instance, **kwargs):
    if not instance.user.hashed_rfid:
        return
    try:
        r = get_redis_client()
        primary_membership = instance.user.memberships.filter(is_primary=True).first()
        if primary_membership:
            r.hset(f"cache:rfid:{instance.user.hashed_rfid}", "primary_unit_id", str(primary_membership.unit.id))
        else:
            r.hset(f"cache:rfid:{instance.user.hashed_rfid}", "primary_unit_id", "")
    except Exception as e:
        logger.error("Failed to update membership cache on delete: %s", e)
