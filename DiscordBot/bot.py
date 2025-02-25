from __future__ import annotations
import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import Intents
from dotenv import load_dotenv
import os
from cogs.role_management import AppBettingButtons, RoleManagementCog
from cogs.channel_messages import ChannelMessagesCog
from cogs.embeds import EmbedsCog

# Load environment variables from token.env file
load_dotenv("token.env")

# Get the token from the environment variable
TOKEN = os.getenv('DISCORD_TOKEN')

# Channel IDs
LOG_CHANNEL_ID = 1341562485638955170 
vivid_channel = 1316598516247826534
chalkboard_channel = 1316599321076043886
underdog_channel = 1332869796693409886
bet_channel = 1313980688101408828
dabble_channel = 1331784740558344312
wannaparlay_channel = 1334642760837500929
support_channel = 1342236528327393371
free_vip_channel = 1312451356400812103
vip_plays_channel = 1312450409079767171
free_picks_channel = 1312448620162715830

IGNORED_ROLE_IDS = [
    1312541194533998683,  #moderator
    1312452817050402826,  #owner
    ]

VIP_ROLE_ID = 1312452597671526471  # Replace with actual ID of the VIP role
FREE_ROLE_ID = 1312538252993105960  # Replace with actual ID of the Free role

# Define the bot
class AIPicks(commands.Bot):
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
        self.add_view(AppBettingButtons())  # add buttons view

bot = AIPicks()

# this is a loop for the check roles command
@bot.event
async def on_member_update(before, after):

    if any(role.id in IGNORED_ROLE_IDS for role in after.roles):
        return

    vip_role = discord.utils.get(after.guild.roles, id=VIP_ROLE_ID)
    free_role = discord.utils.get(after.guild.roles, id=FREE_ROLE_ID)

    if vip_role and free_role:
        #if the vip roles is added and user has free role
        if vip_role in after.roles and free_role in after.roles:
            await after.remove_roles(free_role)
            channel = bot.get_channel(LOG_CHANNEL_ID)
            if channel:
                await channel.send(f"Removed 'Free' role from {after.mention} because they have VIP.")

        # if vip is removed and no free role add the free role
        elif vip_role not in after.roles and free_role not in after.roles:
            await after.add_roles(free_role)
            channel = bot.get_channel(LOG_CHANNEL_ID)
            if channel:
                await channel.send(f"Added 'Free' role to {after.mention} because they don't have VIP.")

@bot.event
async def on_interaction_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.errors.InteractionFailed):
        await interaction.response.send_message("The interaction has failed. Please try again.", ephemeral=True)
    elif isinstance(error, discord.errors.Forbidden):
        await interaction.response.send_message("I don't have permission to do that.", ephemeral=True)
    elif isinstance(error, discord.errors.HTTPException):
        await interaction.response.send_message("There was an issue processing the request.", ephemeral=True)
    else:
        print(f"Unexpected Interaction Error: {error}")
        await interaction.response.send_message("An unexpected error occurred while processing your interaction.", ephemeral=True)

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