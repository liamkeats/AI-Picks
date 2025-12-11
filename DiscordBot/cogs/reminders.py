import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Cog

import datetime
import pytz
from enum import Enum

from .channels.channel_ids import *

halifax_tz = pytz.timezone("America/Halifax")


# AM / PM dropdown
class Meridiem(Enum):
    AM = "AM"
    PM = "PM"


# On / Off dropdown
class ReminderState(Enum):
    ON = "On"
    OFF = "Off"


class ReminderCog(Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_channel_id: int = mod_channel
        self.ai_id = 749718906037338144
        self.mizzy_id = 297540520991916052

        self.reminders_enabled: bool = True  # track state

        try:
            self.reminder_loop.start()
        except RuntimeError:
            # Avoid restarting an already running loop
            pass

    def cog_unload(self):
        self.reminder_loop.cancel()

    # -------------------------------------------------
    # DAILY REMINDER LOOP
    # -------------------------------------------------
    @tasks.loop(time=datetime.time(hour=12, minute=0, tzinfo=halifax_tz))
    async def reminder_loop(self):
        """Runs once per day at the configured time."""
        if not self.reminders_enabled:
            return

        channel = self.bot.get_channel(self.reminder_channel_id)

        if channel:
            message = (
                f"<@{self.mizzy_id}> and <@{self.ai_id}>, "
                "check the results and preview channel. "
                "Update results weekly and post daily teaser pictures."
            )
            await channel.send(message)

    # -------------------------------------------------
    # SLASH COMMAND: /setreminder
    # hour (1–12), minute (0–59), AM/PM, On/Off
    # -------------------------------------------------
    @app_commands.command(
        name="setreminder",
        description="Set the daily reminder time and turn it on or off. (Admins only)",
    )
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        hour="Hour in 12-hour format (1–12)",
        minute="Minute (0–59)",
        period="Select AM or PM",
        enabled="Turn daily reminders On or Off",
    )
    async def set_reminder(
        self,
        interaction: discord.Interaction,
        hour: int,
        minute: int,
        period: Meridiem,
        enabled: ReminderState,
    ):
        """
        Example:
        /setreminder hour:1 minute:30 period:PM enabled:On  ->  1:30 PM, reminders ON
        """

        # Basic validation so the UX is friendly
        if not (1 <= hour <= 12):
            await interaction.response.send_message(
                "❌ Hour must be between **1** and **12**.",
                ephemeral=True,
            )
            return

        if not (0 <= minute <= 59):
            await interaction.response.send_message(
                "❌ Minute must be between **0** and **59**.",
                ephemeral=True,
            )
            return

        # Convert 12-hour + AM/PM → 24-hour
        if period == Meridiem.PM and hour != 12:
            hour_24 = hour + 12
        elif period == Meridiem.AM and hour == 12:
            hour_24 = 0
        else:
            hour_24 = hour

        now = datetime.datetime.now(halifax_tz)

        # Build the next occurrence of this time (today or tomorrow)
        new_time = now.replace(
            hour=hour_24,
            minute=minute,
            second=0,
            microsecond=0,
        )

        if new_time < now:
            new_time += datetime.timedelta(days=1)

        # Always update the loop's scheduled time
        self.reminder_loop.change_interval(time=new_time.timetz())

        # Handle ON / OFF state
        if enabled == ReminderState.OFF:
            self.reminders_enabled = False
            if self.reminder_loop.is_running():
                self.reminder_loop.cancel()

            await interaction.response.send_message(
                (
                    f"🔕 Reminders are now **OFF**.\n"
                    f"When turned back on, they will run at "
                    f"**{hour}:{minute:02d} {period.value}** (Halifax time)."
                ),
                ephemeral=True,
            )
        else:
            self.reminders_enabled = True

            if self.reminder_loop.is_running():
                # Restart so the new time takes effect cleanly
                self.reminder_loop.restart()
            else:
                try:
                    self.reminder_loop.start()
                except RuntimeError:
                    pass

            await interaction.response.send_message(
                (
                    f"⏰ Reminders are now **ON** and set to "
                    f"**{hour}:{minute:02d} {period.value}** (Halifax time)."
                ),
                ephemeral=True,
            )

    # Register the slash command when the cog is loaded
    async def cog_load(self):
        self.bot.tree.add_command(self.set_reminder)
