import asyncio
import time

from discord.ext.commands import AutoShardedBot
from prometheus_client import CollectorRegistry

from Bot import TheRealGearBot
from Util.PromMonitors import PromMonitors


class GearBot(AutoShardedBot):
    STARTUP_COMPLETE = False
    user_messages = 0
    bot_messages = 0
    self_messages = 0
    commandCount = 0
    custom_command_count = 0
    errors = 0
    eaten = 0
    database_errors = 0,
    database_connection = None
    locked = True
    redis_pool = None
    aiosession = None
    being_cleaned = dict()
    metrics_reg = CollectorRegistry()
    version = ""

    def __init__(self, *args, loop=None, **kwargs):
        super().__init__(*args, loop=loop, **kwargs)
        self.metrics = PromMonitors(self)

    def dispatch(self, event_name, *args, **kwargs):
        if "socket" not in event_name not in ["message_edit"]:
            self.metrics.bot_event_counts.labels(event_name=event_name).inc()
        with self.metrics.bot_event_progress.labels(event_name=event_name).track_inprogress():
            f = time.perf_counter_ns if hasattr(time, "perf_counter_ns") else time.perf_counter
            start = f()
            super().dispatch(event_name, *args, **kwargs)
            self.metrics.bot_event_timing.labels(event_name=event_name).observe((f() - start) / 1000000)

    async def _run_event(self, coro, event_name, *args, **kwargs):
        """
        intercept events, block them from running while locked and track
        """
        while (self.locked or not self.STARTUP_COMPLETE) and event_name != "on_ready":
            await asyncio.sleep(0.2)
        await super()._run_event(coro, event_name, *args, **kwargs)

    #### event handlers, basically bouncing everything to TheRealGearBot file so we can hotreload our listeners

    async def on_ready(self):
        await TheRealGearBot.on_ready(self)

    async def on_message(self, message):
        await TheRealGearBot.on_message(self, message)

    async def on_guild_join(self, guild):
        await TheRealGearBot.on_guild_join(guild)

    async def on_guild_remove(self, guild):
        await TheRealGearBot.on_guild_remove(guild)

    async def on_command_error(self, ctx, error):
        await TheRealGearBot.on_command_error(self, ctx, error)

    async def on_error(self, event, *args, **kwargs):
        await TheRealGearBot.on_error(self, event, *args, **kwargs)

    #### reloading
