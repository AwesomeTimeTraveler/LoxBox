
# Incubator Discord Monitor (parallel)

A read-only Discord bot (optional control) that runs **alongside** your existing incubator service. It **subscribes** to the same MQTT status topics (or tails a JSON status file) and posts to Discord without touching the control loop.

## 1) Install
```bash
git clone <this repo> incubator-discord && cd incubator-discord
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2) Configure `.env`
- Set `DISCORD_TOKEN`.
- Set `DISCORD_DEFAULT_CHANNEL_ID` (optional; use `/watch start` to add channels at runtime).
- Point `MQTT_HOST`, `MQTT_STATUS_TOPIC` to your broker/topics.
- Update `SENSOR_FIELD_MAP` to match your payload keys (e.g., `{ "temp_c": "sensors.temp_avg_c", "co2_pct": "co2_per", "o2_pct": "o2_per", "states": "states" }`).
- Optionally set `SENSOR_SCALES` (JSON) to handle unit conversions (e.g., `{ "temp_c": 1.0, "co2_pct": 100 }`). If values look like fractions (≤1.5), the bot auto-converts to percent.
- Leave `DISCORD_ALLOW_CONTROL=false` for read-only.

## 3) Run
```bash
python -m src.main
```
Slash commands: `/status`, `/watch start`, `/watch stop`, `/set_thresholds` (now supports `temp_min_c`, `temp_max_c`, `co2_max_pct`, `o2_min_pct`). If `DISCORD_ALLOW_CONTROL=true` and the user has the `IncubatorAdmin` role: `/control`.

## 4) MQTT payload contract (flexible)
The bot reads *your* keys via `SENSOR_FIELD_MAP`. A minimal payload might be:
```json
{
  "timestamp": "2025-11-07T02:07:00",
  "temp_c": 36.9,
  "CO2_percent": 0.072,  
  "O2_percent": 20.7,
  "states": {"heater": true, "solenoid_A": false}
}
```
If CO₂/O₂ come as fractions (0–1), they are auto-converted to %.

## 5) File fallback
If no MQTT, set `MQTT_ENABLED=false` and point `STATUS_JSON_PATH` at a JSON file following the same mapping rules.

## 6) Safety notes
- Default is **read-only**. Control publishing requires `DISCORD_ALLOW_CONTROL=true` **and** the `IncubatorAdmin` role.
- The bot uses `Intents.none()` and runs as a separate process.

# Incubator Discord Monitor (parallel)

A read-only Discord bot (optional control) that runs **alongside** your existing incubator service. It **subscribes** to the same MQTT status topics (or tails a JSON status file) and posts to Discord without touching the control loop.

## 1) Install
```bash
git clone <this repo> incubator-discord && cd incubator-discord
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2) Configure `.env`
- Set `DISCORD_TOKEN`.
- Set `DISCORD_DEFAULT_CHANNEL_ID` (optional; use `/watch start` to add channels at runtime).
- Point `MQTT_HOST`, `MQTT_STATUS_TOPIC` to your existing broker/topics.
- Leave `DISCORD_ALLOW_CONTROL=false` for read-only.

## 3) Run
```bash
python -m src.main
```
The bot exposes slash commands: `/status`, `/watch start`, `/watch stop`, `/set_thresholds`. If `DISCORD_ALLOW_CONTROL=true` and user has the `IncubatorAdmin` role: `/control`.

## 4) Systemd (production)
```bash
sudo groupadd -f incubator
sudo useradd -r -g incubator -d /opt/incubator-discord -s /usr/sbin/nologin incubator || true
sudo mkdir -p /opt/incubator-discord
sudo cp -r . /opt/incubator-discord
sudo chown -R incubator:incubator /opt/incubator-discord
sudo cp systemd/incubator-discord.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now incubator-discord
```

## 5) MQTT payload contract
The bot expects messages on `MQTT_STATUS_TOPIC` like:
```json
{
  "timestamp": "2025-11-07T02:07:00",
  "temp_c": 36.9,
  "humidity_pct": 72.3,
  "fan_rpm": 780,
  "heater_on": true,
  "dewpoint_c": 31.2,
  "extra": {"pressure_pa": 12}
}
```

## 6) File fallback
If you don't have MQTT, set `MQTT_ENABLED=false` and update `STATUS_JSON_PATH`. The file watcher posts new status when the file's `timestamp` changes.

## 7) Safety notes
- Default is **read-only**. Control publishing requires setting `DISCORD_ALLOW_CONTROL=true` **and** an `IncubatorAdmin` role on Discord.
- Bot uses Discord `Intents.none()`; it does not read member content beyond slash command interactions.
- Separate process & IPC: this bot never imports your incubator code. It only **reads** a status bus.