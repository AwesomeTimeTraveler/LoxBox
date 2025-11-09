from __future__ import annotations
import os
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

load_dotenv()

class Config(BaseModel):
    # Discord
    DISCORD_TOKEN: str
    DISCORD_GUILD_ID: int | None = None
    DISCORD_DEFAULT_CHANNEL_ID: int | None = None
    DISCORD_ALLOW_CONTROL: bool = False
    DISCORD_ALERT_COOLDOWN_SEC: int = 180

    # MQTT
    MQTT_ENABLED: bool = True
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: str | None = None
    MQTT_PASSWORD: str | None = None
    MQTT_CLIENT_ID: str = "incubator-discord"
    MQTT_STATUS_TOPIC: str = "incubator/status/#"
    MQTT_COMMAND_TOPIC: str = "incubator/command"

    # File fallback
    STATUS_JSON_PATH: str = "/var/lib/incubator/status.json"
    STATUS_FILE_POLL_SEC: float = 2.0

    # Defaults
    TEMP_MAX_C: float = 39.0
    TEMP_MIN_C: float = 35.0
    HUMIDITY_MIN_PCT: float = 50.0
    HUMIDITY_MAX_PCT: float = 95.0

    DISPLAY_UNITS_TEMP: str = "C"  # or 'F'

    @classmethod
    def load(cls) -> "Config":
        # Convert some envs
        def as_bool(v: str | None, default: bool) -> bool:
            if v is None: return default
            return v.strip().lower() in {"1", "true", "yes", "y", "on"}

        kwargs = {k: os.getenv(k) for k in cls.model_fields.keys()}
        # Coerce bools
        for b in ["DISCORD_ALLOW_CONTROL", "MQTT_ENABLED"]:
            kwargs[b] = as_bool(kwargs.get(b), getattr(cls, b))
        # Coerce ints
        for i in ["DISCORD_GUILD_ID","DISCORD_DEFAULT_CHANNEL_ID","DISCORD_ALERT_COOLDOWN_SEC","MQTT_PORT"]:
            if kwargs.get(i): kwargs[i] = int(kwargs[i])
        # Coerce floats
        for f in ["TEMP_MAX_C","TEMP_MIN_C","HUMIDITY_MIN_PCT","HUMIDITY_MAX_PCT","STATUS_FILE_POLL_SEC"]:
            if kwargs.get(f): kwargs[f] = float(kwargs[f])
        try:
            return cls(**kwargs)
        except ValidationError as e:
            raise SystemExit(f"Config error: {e}")