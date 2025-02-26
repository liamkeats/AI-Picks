import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Context
from discord.utils import get
from collections import Counter, defaultdict
import asyncio

from .roles.user_roles import *

import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.interactions import Interaction
from collections import Counter
import asyncio

class ParlayBan(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.nominations = Counter()
        self.user_nominations = defaultdict(int)
        self.votes = {}
        self.ban_list = []
        self.voting_active = False
        self.channel_id: int = 1344374500271329320  # Set this to the ban list channel
        self.max_nominations_per_user = 5
        self.poll_message_id: int = None

    @app_commands.command(name="nominate", description="Nominate a player to be banned from parlays this week")
    async def nominate(self, interaction: Interaction, player_name: str):
        """Nominate a player to be banned from parlays this week."""
        if self.voting_active:
            await interaction.response.send_message("Nominations are closed. Voting is in progress.")
            return
        
        user_id = interaction.user.id
        if self.user_nominations[user_id] >= self.max_nominations_per_user:
            await interaction.response.send_message("❌ You have reached your nomination limit (5).", ephemeral=True)
            return

        normalized_name = player_name.lower().strip()
        self.nominations[normalized_name] += 1
        self.user_nominations[user_id] += 1
        await interaction.response.send_message(f"✅ {player_name.title()} has been nominated! ({self.nominations[normalized_name]} votes)")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def start_voting(self, ctx:Context):
        """Start the voting phase after nominations (Admin only)."""

        if not self.nominations:
            await ctx.send("No nominations to vote on!")
            return
        
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            await ctx.send("❌ The `#ban_list` channel was not found.")
            return
        
        self.voting_active = True
        self.user_nominations.clear()
        top_players = self.nominations.most_common(10)  # Get top 10 nominated players
        self.votes = {player[0]: 0 for player in top_players}
        
        embed = Embed(title="🗳️ Parlay Ban List Voting", description="React to vote for a player to be banned this week!", color=discord.Color.red())
        message_content = "\n".join([f"**{i+1}. ** {player[0].title()} " for i, player in enumerate(top_players)])
        embed.add_field(name="Candidates", value=message_content, inline=False)
        poll_message = await channel.send(embed=embed)
        self.poll_message_id = poll_message.id
        
        # Add reactions for voting
        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i in range(len(top_players)):
            await poll_message.add_reaction(reactions[i])
        
        self.bot.add_listener(self.handle_reaction_add, "on_reaction_add")
        await ctx.send("before voting end")
        await asyncio.sleep(60)  # Adjust voting time as needed (e.g., 24 hours)
        await self.end_voting(ctx)
        self.bot.remove_listener(self.handle_reaction_add, "on_reaction_add")
    
    @start_voting.error
    async def start_voting_error(self, ctx: Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command", delete_after=5)

    async def handle_reaction_add(self, reaction, user):
        if user.bot:
            return
        
        message = reaction.message
        if message.author != self.bot.user:
            return
        
        # Ensure only one reaction per user
        for r in message.reactions:
            if r != reaction:
                async for u in r.users():
                    if u.id == user.id:
                        await message.remove_reaction(r.emoji, user)
                        break
    
    async def end_voting(self, ctx: Context):
        print("🔍 DEBUG: end_voting started")
        """End the voting phase and finalize the ban list."""
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            print("❌ ERROR: Ban list channel not found.")
            return
        
        poll_message = await channel.fetch_message(self.poll_message_id)
        reactions = poll_message.reactions
        print(f"🔍 DEBUG: Found {len(reactions)} reactions")  # ✅ Confirm reactions exist
        
        voters = {}
        for i, reaction in enumerate(reactions):
            if i < len(self.votes):
                async for user in reaction.users():
                    print(f"🔍 DEBUG: User {user} reacted with {reaction.emoji}")  # ✅ Check if users are being counted
                    if user != self.bot.user and user.id not in voters:
                        self.votes[list(self.votes.keys())[i]] += 1
                        voters[user.id] = reaction.emoji

        print(f"🔍 DEBUG: Final Vote Counts: {self.votes}")
        
        # Determine the most voted player
        top_voted_players = sorted(self.votes.items(), key=lambda x: x[1], reverse=True)[:3]
        self.ban_list = [player[0].title() for player in top_voted_players]
        print(f"🔍 DEBUG: Final Ban List: {self.ban_list}")

        self.nominations.clear()
        self.voting_active = False
        print(f"🔍 DEBUG: Voting Active Status: {self.voting_active}")

        ban_list_message = "\n".join([f"🚫 {player[0].title()} ({player[1]} votes)" for player in top_voted_players])
        embed = Embed(title="🚨 Weekly Parlay Ban List", description=ban_list_message if ban_list_message else "No players received votes.", color=discord.Color.red())
        
        if channel:
            print(f"🔍 DEBUG: Sending final ban list to {channel.name}")
            await channel.send(embed=embed)

    @app_commands.command(name="show_banlist", description="View the current week's banned players.")
    async def show_banlist(self, interaction: Interaction):
        """Show the current week's ban list."""
        if not self.ban_list:
            await interaction.response.send_message("No players are currently banned from parlays.")
        else:
            await interaction.response.send_message("🚫 **Weekly Ban List:**\n" + "\n".join(self.ban_list))
