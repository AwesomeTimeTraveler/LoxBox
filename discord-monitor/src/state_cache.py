from __future__ import annotations
from collections import deque
from datetime import datetime, timedelta
from typing import Optional
from .models import IncubatorStatus

class StateCache:
    def __init__(self, cooldown_sec: int = 180):
        self.latest: Optional[IncubatorStatus] = None
        self.history: deque[IncubatorStatus] = deque(maxlen=500)
        self.last_alert_at: dict[str, datetime] = {}
        self.cooldown = timedelta(seconds=cooldown_sec)

    def update(self, st: IncubatorStatus):
        self.latest = st
        self.history.append(st)

    def can_alert(self, key: str) -> bool:
        now = datetime.utcnow()
        last = self.last_alert_at.get(key)
        if not last or (now - last) >= self.cooldown:
            self.last_alert_at[key] = now
            return True
        return False