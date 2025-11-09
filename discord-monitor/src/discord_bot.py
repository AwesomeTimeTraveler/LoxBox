## src/discord_bot.py

```python
from __future__ import annotations
import asyncio, logging, os
import discord
from discord import app_commands
from discord.ext import tasks

try:
    import psutil  # optional; used for system line
except Exception:  # pragma: no cover
    psutil = None

from .state_cache import StateCache
from .alerts import Thresholds
from .models import IncubatorStatus

log = logging.getLogger(__name__)






class IncubatorDiscord(discord.Client):
    def __init__(self, *, cache: StateCache, thresholds: Thresholds, guild_id: int | None, allow_control: bool, units: str):
        intents = discord.Intents.none()  # read-only
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.cache = cache
        self.thresholds = thresholds
        self.guild_id = guild_id
        self.allow_control = allow_control
        self.units = units
        self._watch_channels: set[int] = set()
        # Presentation flags (read from env so we don't need to touch config.py)
        self.use_embeds = os.getenv("USE_EMBEDS", "true").lower() in {"1","true","yes","y","on"}
        self.show_system = os.getenv("SHOW_SYSTEM_LINE", "true").lower() in {"1","true","yes","y","on"}

    async def setup_hook(self):
        if self.guild_id:
            guild = discord.Object(id=self.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    # ---------- Helpers ----------
    def _system_line(self) -> str | None:
        if not self.show_system:
            return None
        try:
            if psutil is None:
                return "System: psutil not installed"
            cpu = psutil.cpu_percent(interval=None)
            vm = psutil.virtual_memory()
            used_mb = int(vm.used / (1024*1024))
            total_mb = int(vm.total / (1024*1024))
            return f"System: CPU {cpu:.1f}% | Mem {used_mb}/{total_mb} MB ({vm.percent:.0f}%)"
        except Exception as e:  # robust to odd platforms
            return f"System: n/a ({e})"

    def _status_lines(self, s: IncubatorStatus) -> list[str]:
        lines = s.as_lines(self.units)
        sysln = self._system_line()
        if sysln:
            lines.append(sysln)
        return lines

    def _status_title_and_color(self, s: IncubatorStatus) -> tuple[str, int]:
        # Color code embeds based on threshold checks
        issues = self.thresholds.check(s)
        if issues:
            return ("Incubator Status — ALERT", 0xD83A3A)  # red
        return ("Incubator Status", 0x1F8B4C)  # greenish


    # ---------- Slash commands ----------
    @app_commands.command(name="status", description="Show latest incubator status")
    async def status_cmd(self, interaction: discord.Interaction):
        st = self.cache.latest
        if not st:
            await interaction.response.send_message("No status yet.")
            return
        msg = self.build_message(st)
        await interaction.response.send_message(content=msg["content"], embed=msg["embed"])  # type: ignore[arg-type]

    @app_commands.command(name="watch", description="Post status updates into this channel (start/stop)")
    @app_commands.describe(action="start or stop")
    async def watch_cmd(self, interaction: discord.Interaction, action: str):
        action = action.lower()
        ch_id = interaction.channel_id
        if action == "start":
            self._watch_channels.add(ch_id)
            await interaction.response.send_message("Watching this channel for updates.")
        elif action == "stop":
            self._watch_channels.discard(ch_id)
            await interaction.response.send_message("Stopped watching this channel.")
        else:
            await interaction.response.send_message("Use 'start' or 'stop'.")

    @app_commands.command(name="set_thresholds", description="Set alert thresholds (global)")
    async def set_thresholds_cmd(self, interaction: discord.Interaction, temp_min_c: float | None = None, temp_max_c: float | None = None, co2_max_pct: float | None = None, o2_min_pct: float | None = None):
        self.thresholds.t_min = temp_min_c
        self.thresholds.t_max = temp_max_c
        self.thresholds.co2_max = co2_max_pct
        self.thresholds.o2_min = o2_min_pct
        await interaction.response.send_message("Thresholds updated.")

    @app_commands.command(name="control", description="(Optional) send control intent via MQTT (admin only)")
    async def control_cmd(self, interaction: discord.Interaction, command: str, value: str | None = None):
        if not self.allow_control:
            await interaction.response.send_message("Control is disabled.")
            return
        roles = [r.name for r in getattr(interaction.user, 'roles', [])]
        if 'IncubatorAdmin' not in roles:
            await interaction.response.send_message("Insufficient role.")
            return
        await interaction.response.defer(thinking=True)
        put = self.__class__.publish_queue.put_nowait  # type: ignore[attr-defined]
        put((command, value))
        await interaction.followup.send(f"Queued control: {command} {value or ''}")

    # ---------- Background loops ----------
    @tasks.loop(seconds=10)
    async def heartbeat(self):
        st = self.cache.latest
        if not st:
            return
        msg = self.build_message(st)
        for ch_id in list(self._watch_channels):
            ch = self.get_channel(ch_id)
            if ch is None:
                continue
            try:
                await ch.send(content=msg["content"], embed=msg["embed"])  # type: ignore[arg-type]
            except Exception:
                log.warning("Failed to post to channel %s", ch_id)

    @heartbeat.before_loop
    async def before_heartbeat(self):
        await self.wait_until_ready()

    async def broadcast_alert(self, text: str):
        # Alerts are simple text so they stand out even with embeds
        for ch_id in list(self._watch_channels):
            ch = self.get_channel(ch_id)
            if ch:
                try:
                    await ch.send(f"⚠️ {text}")
                except Exception:
                    log.warning("Failed to alert channel %s", ch_id)

    async def on_ready(self):
        log.info("Discord bot ready as %s", self.user)
        self.heartbeat.start()














    def build_message(self, s: IncubatorStatus):
        lines = self._status_lines(s)
        timestamp = s.timestamp.isoformat(timespec='seconds') + 'Z'

        if self.use_embeds:
            title, color = self._status_title_and_color(s)
            emb = discord.Embed(
                title=title,
                description="\n".join(lines),
                color=color
            )
            emb.set_footer(text=timestamp)
            return {"content": None, "embed": emb}
        else:
            formatted = (
                "**Incubator Status**\n"
                + "\n".join(lines)
                + f"\n`{timestamp}`"
            )
            return {"content": formatted, "embed": None}
