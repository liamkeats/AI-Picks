from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context
from discord import app_commands, Interaction
from .other.stream_links import *


class ChannelMessagesCog(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        super().__init__()

    # hello command to check if bot is running
    @commands.command()
    async def hello(self, ctx: Context):
        await ctx.send("Hello! I am alive and running.")

    #command for users to find stream links
    @app_commands.command(name="findstream", description="This command shows available streaming links to watch games at your convinience")
    async def findstream(self, interaction:Interaction):
        # Multi-line string for links
        links_message = "\n".join(links)
        # Send the message with code formatting to clean up the output
        await interaction.response.send_message(f"Available streaming links:\n{links_message}")