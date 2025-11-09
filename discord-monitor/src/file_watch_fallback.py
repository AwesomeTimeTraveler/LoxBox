from __future__ import annotations
import asyncio, json, logging
from datetime import datetime
from .models import IncubatorStatus
from .state_cache import StateCache
from .mqtt_bus import resolve, to_percent

log = logging.getLogger(__name__)

class FileWatch:
    def __init__(self, path: str, poll_sec: float, cache: StateCache, field_map: dict, scales: dict):
        self.path = path
        self.poll = poll_sec
        self.cache = cache
        self.field_map = field_map
        self.scales = scales

    async def run(self):
        log.info(f"Watching status file: {self.path}")
        last = None
        while True:
            try:
                with open(self.path, 'r') as f:
                    payload = json.load(f)
                ts = payload.get("timestamp")
                if ts != last:
                    last = ts
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
            except FileNotFoundError:
                log.warning("Status file not found yet…")
            except Exception as e:
                log.warning(f"Status file parse error: {e}")
            await asyncio.sleep(self.poll)