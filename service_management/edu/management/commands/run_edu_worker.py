import logging
from django.core.management.base import BaseCommand
from edu import worker
import redis
import orjson
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Run the Edu worker to process tap events from Redis streams'

    def handle(self, *args, **kwargs):
        logger.error("Edu Worker started")
        
        try:
            r = redis.Redis(host='redis', port=6379, decode_responses=True)
            logger.error("Connected to Redis")
        except Exception as e:
            logger.error("Failed to connect to Redis: %s", e)
            return
        
        streams = {
            'stream:edu': '$',
        }
        
        while True:
            try:
                result = r.xread(streams, block=5000)
                
                for stream_name, messages in result:
                    for message_id, fields in messages:
                        try:
                            data = orjson.loads(fields.get('data', '{}'))
                            logger.info("Processing Edu tap: %s", data)
                            
                            success = worker.process_edu_tap(data)
                            
                            if success:
                                logger.info("Successfully processed tap for user %s", data.get('user_id'))
                            else:
                                logger.error("Failed to process tap for user %s", data.get('user_id'))
                                
                        except Exception as e:
                            logger.error("Error processing message: %s", e)
                            
            except Exception as e:
                logger.error("Error reading from stream: %s", e)
                time.sleep(1)
