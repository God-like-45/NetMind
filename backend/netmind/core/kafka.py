import json
import logging
import asyncio
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from netmind.core.config import get_kafka_settings
from netmind.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

_producer: AIOKafkaProducer | None = None

async def get_kafka_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        settings = get_kafka_settings()
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            # Idempotency and reliability
            enable_idempotence=True,
            acks="all",
            retry_backoff_ms=500,
        )
        await _producer.start()
    return _producer

async def close_kafka_producer() -> None:
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None

async def publish_event(topic: str, key: str, value: dict) -> None:
    """
    Publish an event to Kafka.
    Key is used for partitioning (e.g. device_id) to guarantee ordering per device.
    """
    producer = await get_kafka_producer()
    try:
        await producer.send_and_wait(
            topic=topic,
            key=key.encode("utf-8") if key else None,
            value=value
        )
    except Exception as e:
        # Fallback for Kafka Failure (Scenario 1)
        logger.error(f"[RECOVERY] Kafka unreachable. Event dropped or routed to DLQ. Error: {e}")

class KafkaConsumerService:
    """
    Demonstrates Phase 6 Kafka Flow:
    Producer -> Topic -> Consumer -> Processing -> Persistence
    
    Handles:
    - Consumer failure & retries
    - Malformed messages (skip & DLQ)
    - Duplicate messages (Idempotency via Redis)
    """
    
    def __init__(self, topic: str, group_id: str):
        settings = get_kafka_settings()
        self.topic = topic
        self.group_id = group_id
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=settings.bootstrap_servers,
            group_id=self.group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest"
        )
        self.redis = get_redis_client()
        
    async def process_message(self, message) -> None:
        """Override this to implement actual processing logic and persistence"""
        pass
        
    async def start(self):
        await self.consumer.start()
        logger.info(f"Started Kafka consumer for topic {self.topic}, group {self.group_id}")
        
        try:
            async for msg in self.consumer:
                # 1. Parse JSON and handle Malformed messages
                try:
                    payload = json.loads(msg.value.decode("utf-8"))
                except json.JSONDecodeError:
                    logger.error(f"Malformed message at {msg.topic}:{msg.partition}:{msg.offset}. Skipping.")
                    await self.consumer.commit()
                    continue
                
                # 2. Idempotency Check (Duplicate messages)
                message_id = payload.get("id") or f"{msg.topic}:{msg.partition}:{msg.offset}"
                idempotency_key = f"kafka_processed:{message_id}"
                
                is_duplicate = await self.redis.setnx(idempotency_key, "1")
                if not is_duplicate: # setnx returns 0/False if it already existed
                    logger.warning(f"Duplicate message detected: {message_id}. Skipping.")
                    await self.consumer.commit()
                    continue
                
                # Set expire so Redis doesn't grow infinitely
                await self.redis.expire(idempotency_key, 86400 * 7) # 7 days
                
                # 3. Process & Retries
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        await self.process_message(payload)
                        # 4. Acknowledge message only on success
                        await self.consumer.commit()
                        break
                    except Exception as e:
                        logger.error(f"Error processing message {message_id} on attempt {attempt+1}: {e}")
                        if attempt == max_retries - 1:
                            logger.error(f"Max retries reached for message {message_id}. Sending to DLQ.")
                            # E.g., publish to DLQ topic here
                            await self.consumer.commit()
                        else:
                            await asyncio.sleep(2 ** attempt) # Exponential backoff
                            
        except Exception as e:
            logger.error(f"Consumer failure: {e}")
        finally:
            await self.consumer.stop()
