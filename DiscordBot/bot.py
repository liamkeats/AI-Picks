from __future__ import annotations
import discord
import os

from discord.ext import commands
from discord.ext.commands import Context, Bot
from discord import Intents
from dotenv import load_dotenv

from cogs.role_management import AppBettingButtons, RoleManagementCog, SportSelectionButtons
from cogs.channel_messages import ChannelMessagesCog
from cogs.embeds import EmbedsCog
from cogs.banned_players import ParlayBan
from cogs.welcome import Welcome
from cogs.reminders import ReminderCog

# Load environment variables from token.env file
load_dotenv("token.env")

# Get the token from the environment variable
TOKEN = os.getenv('DISCORD_TOKEN')

# Define the bot
class AIPicks(Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True  # Enable member-related events
        intents.message_content = True  # Enable message content reading
        intents.reactions = True 
        super().__init__(command_prefix="!", intents=Intents.all())

    async def setup_hook(self):
        # Register the view once the bot is ready
        await self.add_cog(RoleManagementCog(self))
        await self.add_cog(ChannelMessagesCog(self))
        await self.add_cog(EmbedsCog(self))
        await self.add_cog(ParlayBan(self))
        await self.add_cog(Welcome(self))
        await self.add_cog(ReminderCog(self))
        
        self.add_view(AppBettingButtons())
        self.add_view(SportSelectionButtons())

bot = AIPicks()

# starting the bot
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

    #await check_roles()

@bot.command()
@commands.is_owner()
async def sync(ctx:Context):
    message = await ctx.send("Syncing commands")
    commands_synced = await bot.tree.sync()
    await message.edit(content=f"Synced {len(commands_synced)} commands")


# Run the bot with your token
bot.run(TOKEN)