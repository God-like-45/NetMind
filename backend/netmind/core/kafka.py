import json
import logging
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from netmind.core.config import get_kafka_settings

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
