import logging
from django.core.management.base import BaseCommand
from sterling_core.models import Unit, SterlingUser, Membership
import redis

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Warm Redis cache with Unit and User data for high-speed ingestion'

    def handle(self, *args, **kwargs):
        try:
            r = redis.Redis(host='redis', port=6379, decode_responses=True)
            r.ping()
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            return

        self.stdout.write("Warming Unit cache...")
        unit_count = 0
        for unit in Unit.objects.select_related('organization').all():
            try:
                r.hset(f"cache:unit:{unit.id}", mapping={
                    "org_id": str(unit.organization.id),
                    "vertical": "SCHOOL"
                })
                unit_count += 1
            except Exception as e:
                logger.error("Failed to cache unit %s: %s", unit.id, e)
        self.stdout.write(self.style.SUCCESS(f"Cached {unit_count} units"))

        self.stdout.write("Warming RFID cache...")
        rfid_count = 0
        for user in SterlingUser.objects.filter(hashed_rfid__isnull=False).exclude(hashed_rfid='').all():
            try:
                primary_membership = user.memberships.filter(is_primary=True).first()
                primary_unit_id = str(primary_membership.unit.id) if primary_membership else ""
                r.hset(f"cache:rfid:{user.hashed_rfid}", mapping={
                    "user_id": str(user.id),
                    "primary_unit_id": primary_unit_id
                })
                rfid_count += 1
            except Exception as e:
                logger.error("Failed to cache RFID for user %s: %s", user.id, e)
        self.stdout.write(self.style.SUCCESS(f"Cached {rfid_count} RFID entries"))

        self.stdout.write(self.style.SUCCESS("Cache warming complete!"))
        r.close()
