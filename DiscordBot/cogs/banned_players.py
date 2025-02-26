import discord
from discord import app_commands, Interaction, Embed
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Context
from collections import Counter
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
        self.votes = {}
        self.ban_list = []
        self.voting_active = False
        self.channel_id = None  # Set this to the ban list channel

    @app_commands.command(name="nominate", description="Nominate a player to be banned from parlays this week")
    async def nominate(self, interaction: Interaction, player_name: str):
        """Nominate a player to be banned from parlays this week."""
        if self.voting_active:
            await interaction.response.send_message("Nominations are closed. Voting is in progress.")
            return
        
        normalized_name = player_name.lower().strip()
        self.nominations[normalized_name] += 1
        await interaction.response.send_message(f"✅ {player_name.title()} has been nominated! ({self.nominations[normalized_name]} votes)")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def start_voting(self, ctx:Context):
        """Start the voting phase after nominations (Admin only)."""

        if not self.nominations:
            await ctx.send("No nominations to vote on!")
            return
        
        self.voting_active = True
        top_players = self.nominations.most_common(10)  # Get top 10 nominated players
        self.votes = {player[0]: 0 for player in top_players}
        
        embed = Embed(title="🗳️ Parlay Ban List Voting", description="React to vote for a player to be banned this week!", color=discord.Color.red())
        message_content = "\n".join([f"**{i+1}.** {player[0].title()}" for i, player in enumerate(top_players)])
        embed.add_field(name="Candidates", value=message_content, inline=False)
        poll_message = await ctx.send(embed=embed)
        
        # Add reactions for voting
        reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for i in range(len(top_players)):
            await poll_message.add_reaction(reactions[i])
        
        self.bot.add_listener(self.handle_reaction_add, "on_reaction_add")
        await asyncio.sleep(60)  # Adjust voting time as needed (e.g., 24 hours)
        await self.end_voting(ctx, poll_message)
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
    
    async def end_voting(self, ctx: Context, poll_message):
        """End the voting phase and finalize the ban list."""
        poll_message = await ctx.channel.fetch_message(poll_message.id)
        reactions = poll_message.reactions
        voters = {}
        
        for i, reaction in enumerate(reactions):
            if i < len(self.votes):
                async for user in reaction.users():
                    if user != self.bot.user and user.id not in voters:
                        self.votes[list(self.votes.keys())[i]] += 1
                        voters[user.id] = reaction.emoji
        
        # Determine the most voted player
        most_voted_player = max(self.votes.items(), key=lambda x: x[1], default=None)
        self.ban_list = [most_voted_player[0].title()] if most_voted_player else []
        self.nominations.clear()
        self.voting_active = False
        
        ban_list_message = f"🚫 {most_voted_player[0]} ({most_voted_player[1]} votes)" if most_voted_player else "No players received votes."
        embed = Embed(title="🚨 Weekly Parlay Ban List", description=ban_list_message, color=discord.Color.red())
        
        if self.channel_id:
            channel = self.bot.get_channel(self.channel_id)
            await channel.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @app_commands.command(name="show_banlist", description="View the current week's banned players.")
    async def show_banlist(self, interaction: Interaction):
        """Show the current week's ban list."""
        if not self.ban_list:
            await interaction.response.send_message("No players are currently banned from parlays.")
        else:
            await interaction.response.send_message("🚫 **Weekly Ban List:**\n" + "\n".join(self.ban_list))
