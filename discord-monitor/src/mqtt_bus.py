from __future__ import annotations
import asyncio, json, logging
from asyncio_mqtt import Client, MqttError
from datetime import datetime
from backoff import expo, on_exception
from .models import IncubatorStatus
from .state_cache import StateCache

log = logging.getLogger(__name__)

# Helper: resolve a value from payload with mapping key (supports dotted paths)
def resolve(payload: dict, key: str | None):
    if not key:
        return None
    cur = payload
    for part in key.split('.'):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur

# Helper: convert possibly-fractional percentages to percent
def to_percent(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    # Auto-detect: if looks like fraction, scale
    if 0 <= x <= 1.5:
        return x * 100.0
    return x

class MQTTBus:
    def __init__(self, host: str, port: int, topic: str, client_id: str, username: str|None, password: str|None, cache: StateCache, field_map: dict, scales: dict):
        self.host=host; self.port=port; self.topic=topic; self.client_id=client_id
        self.username=username; self.password=password
        self.cache=cache
        self.field_map = field_map
        self.scales = scales

    @on_exception(expo, (MqttError, ConnectionError), max_time=300)
    async def run(self):
        auth = {}
        if self.username:
            auth = {"username": self.username, "password": self.password}
        async with Client(self.host, self.port, client_id=self.client_id, **auth) as client:
            log.info(f"MQTT connected to {self.host}:{self.port}, sub {self.topic}")
            async with client.messages() as messages:
                await client.subscribe(self.topic)
                async for message in messages:
                    try:
                        payload = json.loads(message.payload.decode())
                        ts = payload.get("timestamp")
                        temp_key = self.field_map.get("temp_c")
                        co2_key = self.field_map.get("co2_pct")
                        o2_key  = self.field_map.get("o2_pct")
                        states_key = self.field_map.get("states")

                        temp_v = resolve(payload, temp_key)
                        if temp_v is None:
                            raise ValueError("Missing temp value; map temp_c in SENSOR_FIELD_MAP")
                        temp_c = float(temp_v) * float(self.scales.get("temp_c", 1.0))

                        co2_raw = resolve(payload, co2_key)
                        o2_raw  = resolve(payload, o2_key)
                        co2_pct = to_percent(co2_raw) if co2_raw is not None else None
                        o2_pct  = to_percent(o2_raw) if o2_raw is not None else None
                        if co2_pct is not None:
                            co2_pct *= float(self.scales.get("co2_pct", 1.0))
                        if o2_pct is not None:
                            o2_pct *= float(self.scales.get("o2_pct", 1.0))

                        states = resolve(payload, states_key) or {}
                        if not isinstance(states, dict):
                            states = {}

                        st = IncubatorStatus(
                            timestamp = datetime.fromisoformat(ts) if isinstance(ts,str) else datetime.utcnow(),
                            temp_c = temp_c,
                            co2_pct = co2_pct,
                            o2_pct = o2_pct,
                            states = {str(k): bool(v) for k,v in states.items()},
                            extra = {k:v for k,v in payload.items() if k not in {temp_key, co2_key, o2_key, states_key, 'timestamp'}}
                        )
                        self.cache.update(st)
                    except Exception as e:
                        log.warning(f"Bad MQTT payload: {e}")

    @on_exception(expo, (MqttError, ConnectionError), max_time=120)
    async def publish_command(self, topic: str, payload: dict):
        auth = {}
        if self.username:
            auth = {"username": self.username, "password": self.password}
        async with Client(self.host, self.port, client_id=self.client_id+"-pub", **auth) as client:
            await client.publish(topic, json.dumps(payload), qos=1)