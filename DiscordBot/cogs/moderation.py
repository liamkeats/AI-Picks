import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction
from discord.ext.commands import Cog

from .channels.channel_ids import *

class Moderation(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id: int = logs_channel

    @app_commands.command(name="mute", description="mute a user")
    async def mute(self, interaction: Interaction, user_name):
        
