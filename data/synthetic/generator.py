import asyncio
import json
import random
import time
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer

# Kafka settings
KAFKA_BOOTSTRAP_SERVERS = "localhost:9093"
TOPIC_TELEMETRY = "netmind.telemetry"

# List of mock network devices
DEVICES = [
    {"id": "router-core-01", "type": "router", "site": "NYC"},
    {"id": "router-core-02", "type": "router", "site": "LDN"},
    {"id": "switch-access-01", "type": "switch", "site": "NYC"},
    {"id": "fw-edge-01", "type": "firewall", "site": "LDN"},
]

def generate_telemetry(device):
    """Generate fake telemetry data for a device."""
    # Base normal metrics
    cpu = random.uniform(10.0, 45.0)
    memory = random.uniform(30.0, 70.0)
    temperature = random.uniform(35.0, 50.0)
    
    # 5% chance to create an "anomaly" (spike)
    if random.random() < 0.05:
        cpu = random.uniform(85.0, 99.0)
        print(f"Anomaly injected for {device['id']}")

    return {
        "device_id": device["id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "cpu_usage_percent": round(cpu, 2),
            "memory_usage_percent": round(memory, 2),
            "temperature_celsius": round(temperature, 2),
            "active_connections": random.randint(100, 5000)
        }
    }

async def produce_telemetry():
    """Continuously stream telemetry data to Kafka."""
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    await producer.start()
    print(f"Connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Starting synthetic telemetry stream to topic '{TOPIC_TELEMETRY}'...\n")
    
    try:
        while True:
            for device in DEVICES:
                payload = generate_telemetry(device)
                await producer.send_and_wait(TOPIC_TELEMETRY, payload)
                print(f"Sent: {payload['device_id']} | CPU: {payload['metrics']['cpu_usage_percent']}%")
            
            # Wait 2 seconds before the next batch
            await asyncio.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping telemetry generator...")
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(produce_telemetry())
