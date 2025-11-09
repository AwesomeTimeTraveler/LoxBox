from __future__ import annotations
import asyncio, logging, os, json
from logging import INFO
from datetime import datetime
from src.config import Config
from src.logging_setup import setup_logging
from src.state_cache import StateCache
from src.alerts import Thresholds
from src.mqtt_bus import MQTTBus
from src.file_watch_fallback import FileWatch
from src.discord_bot import IncubatorDiscord

async def run_async():
    setup_logging(INFO)
    cfg = Config.load()
    log = logging.getLogger("main")

    # Parse JSON mapping/scales from env
    try:
        field_map = json.loads(os.getenv("SENSOR_FIELD_MAP", "{}"))
    except json.JSONDecodeError:
        raise SystemExit("SENSOR_FIELD_MAP must be valid JSON")
    try:
        scales = json.loads(os.getenv("SENSOR_SCALES", "{}"))
    except json.JSONDecodeError:
        raise SystemExit("SENSOR_SCALES must be valid JSON")

    cache = StateCache(cooldown_sec=cfg.DISCORD_ALERT_COOLDOWN_SEC)
    thresholds = Thresholds(
        t_min=cfg.TEMP_MIN_C if os.getenv("TEMP_MIN_C") else None,
        t_max=cfg.TEMP_MAX_C if os.getenv("TEMP_MAX_C") else None,
        co2_max=float(os.getenv("CO2_MAX_PCT")) if os.getenv("CO2_MAX_PCT") else None,
        o2_min=float(os.getenv("O2_MIN_PCT")) if os.getenv("O2_MIN_PCT") else None,
    )

    # Data source task (MQTT or file)
    tasks = []
    mqtt_bus: MQTTBus | None = None
    if cfg.MQTT_ENABLED:
        mqtt_bus = MQTTBus(
            host=cfg.MQTT_HOST,
            port=cfg.MQTT_PORT,
            topic=cfg.MQTT_STATUS_TOPIC,
            client_id=cfg.MQTT_CLIENT_ID,
            username=cfg.MQTT_USERNAME,
            password=cfg.MQTT_PASSWORD,
            cache=cache,
            field_map=field_map,
            scales=scales,
        )
        tasks.append(asyncio.create_task(mqtt_bus.run(), name="mqtt-run"))
        log.info("MQTT mode enabled")
    else:
        fw = FileWatch(cfg.STATUS_JSON_PATH, cfg.STATUS_FILE_POLL_SEC, cache, field_map, scales)
        tasks.append(asyncio.create_task(fw.run(), name="file-watch"))
        log.info("File-watch mode enabled")

    # Discord client
    bot = IncubatorDiscord(
        cache=cache,
        thresholds=thresholds,
        guild_id=cfg.DISCORD_GUILD_ID,
        allow_control=cfg.DISCORD_ALLOW_CONTROL,
        units=cfg.DISPLAY_UNITS_TEMP,
    )

    async def alert_pump():
        last_seen = None
        while True:
            st = cache.latest
            if st and st is not last_seen:
                last_seen = st
                issues = thresholds.check(st)
                for issue in issues:
                    key = issue.split(':', 1)[0]
                    if cache.can_alert(key):
                        await bot.broadcast_alert(issue)
            await asyncio.sleep(1)

    tasks.append(asyncio.create_task(alert_pump(), name="alerts"))

    # Optional control queue wiring (only active if control is enabled + MQTT)
    if cfg.DISCORD_ALLOW_CONTROL and mqtt_bus:
        IncubatorDiscord.publish_queue = asyncio.Queue()  # type: ignore[attr-defined]

        async def control_pump():
            while True:
                cmd, val = await IncubatorDiscord.publish_queue.get()  # type: ignore[attr-defined]
                payload = {"command": cmd, "value": val, "source": "discord", "ts": datetime.utcnow().isoformat()}
                try:
                    await mqtt_bus.publish_command(cfg.MQTT_COMMAND_TOPIC, payload)
                except Exception as e:
                    logging.getLogger("control").warning("Failed to publish control: %s", e)

        tasks.append(asyncio.create_task(control_pump(), name="control"))

    async def run_discord():
        await bot.start(os.environ["DISCORD_TOKEN"])  # token already validated by Config

    tasks.append(asyncio.create_task(run_discord(), name="discord"))

    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.cancel()

if __name__ == "__main__":
    asyncio.run(run_async())