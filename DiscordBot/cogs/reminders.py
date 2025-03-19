import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Cog

import datetime
import pytz

from .channels.channel_ids import *

halifax_tz = pytz.timezone("America/Halifax")

class ReminderCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminder_channel_id: int = mod_channel
        self.ai_id = 749718906037338144  # Replace with actual user ID
        self.mizzy_id = 297540520991916052  # Replace with actual user ID
        
        try:
            self.reminder_loop.start()
        except RuntimeError:
            pass  # Avoid restarting an already running loop

    def cog_unload(self):
        self.reminder_loop.cancel()

    @tasks.loop(time=datetime.time(hour=12, minute=0, tzinfo=halifax_tz))  # Runs at 12:00 Halifax Time
    async def reminder_loop(self):
        """Sends a reminder message at the scheduled time."""
        channel = self.bot.get_channel(self.reminder_channel_id)
        
        if channel:
            message = f"<@{self.mizzy_id}> and <@{self.ai_id}>, check the results and preview channel. Update results once a week or so and update the preview channel daily with teaser pictures."
            await channel.send(message)

    @commands.command(name="setreminder")
    @commands.has_permissions(administrator=True)
    async def set_reminder(self, ctx, hour: int, minute: int):
        """Allows an admin to change the reminder time dynamically and ensures it runs at the next occurrence."""

        # Convert the current time to Halifax timezone
        now = datetime.datetime.now(halifax_tz)
        new_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If the new time is in the past today, schedule it for tomorrow
        if new_time < now:
            new_time += datetime.timedelta(days=1)

        # Change the reminder interval
        self.reminder_loop.change_interval(time=new_time.timetz())

        if self.reminder_loop.is_running():
            self.reminder_loop.restart()
        else:
            try:
                self.reminder_loop.start()
            except RuntimeError:
                pass  # Avoid error if the loop is already running

        await ctx.send(f"Reminder time updated to {hour:02}:{minute:02}, and it will send at that time!")
