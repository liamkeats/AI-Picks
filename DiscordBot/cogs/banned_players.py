import discord
import difflib
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Context
from discord.ui import View, Button

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
import asyncio
from datetime import datetime, timezone

from .roles.user_roles import *
from cogs.other.player_names import * 

load_dotenv("token.env")
PASSWORD = os.getenv('MONGO_PASSWORD')
PASSWORD = quote_plus(PASSWORD)

uri = f"mongodb+srv://keatsliam:{PASSWORD}@aipicks.cdvhr.mongodb.net/?retryWrites=true&w=majority&appName=AiPicks"
client = MongoClient(uri, server_api=ServerApi('1'))

db = client["AI_Picks_Bot"]
nominations_collection = db["nominations"]
user_nominations_collection = db["user_nominations"]
ban_list_collection = db["ban_list"]
user_votes_collection = db["user_votes"]


class BanListVoting(View):
    def __init__(self, top_players):
        super().__init__(timeout=None)
        self.top_players = top_players

        for player in top_players:
            button = Button(label=player["player_name"], style=ButtonStyle.primary)
            button.callback = self.create_vote_callback(player["player_name"])
            self.add_item(button)

    def create_vote_callback(self, player_name):
        async def vote_callback(interaction: Interaction):
            user_id = interaction.user.id

            # Check if the user already voted
            existing_vote = user_votes_collection.find_one({"voted_by": user_id})
            if existing_vote:
                await interaction.response.send_message("❌ You have already voted!", ephemeral=True)
                return
            
            # Store the vote in `user_votes`
            user_votes_collection.insert_one({
                "voted_for": player_name,
                "voted_by": user_id
            })

            await interaction.response.send_message(f"✅ You voted for {player_name}!", ephemeral=True)

        return vote_callback

class ParlayBan(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id: int = 1344374500271329320  # Ban list channel ID
        self.max_nominations_per_user = 5
        self.poll_message_id: int = None

    @app_commands.command(name="nominate", description="Nominate a player to be banned from parlays this week")
    async def nominate(self, interaction: Interaction, player_name: str):
        """Nominate a player to be banned from parlays this week."""
        
        voting_status = db["voting_state"].find_one({"status": "active"})
        if voting_status:
            await interaction.response.send_message("Nominations are closed. Voting is in progress.")
            return

        # Correct spelling if needed
        original_name = player_name
        nba_players = player_names
        matches = difflib.get_close_matches(player_name, nba_players, n=3, cutoff=0.6)
        
        if matches:
            player_name = matches[0]
        else:
            await interaction.response.send_message(f"❌ `{player_name}` not found. Please check spelling!", ephemeral=True)
            return
        
        user_id = interaction.user.id
        user_entry = user_nominations_collection.find_one({"user_id": user_id})

        if not user_entry:
            user_nominations_collection.insert_one({"user_id": user_id, "nominated_players": []})

        user_entry = user_nominations_collection.find_one({"user_id": user_id})
        if len(user_entry["nominated_players"]) >= self.max_nominations_per_user:
            await interaction.response.send_message("❌ You have reached your nomination limit (5).", ephemeral=True)
            return

        player_entry = nominations_collection.find_one({"player_name": player_name})

        if player_entry:
            nominations_collection.update_one(
                {"player_name": player_name},
                {"$inc": {"votes": 1}, "$addToSet": {"nominated_by": user_id}}
            )
        else:
            nominations_collection.insert_one({
                "player_name": player_name,
                "nominated_by": [user_id],
                "votes": 1
            })
        user_nominations_collection.update_one(
            {"user_id": user_id},
            {"$push": {"nominated_players": player_name}}
        )

        await interaction.response.send_message(f"✅ {player_name.title()} has been nominated!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def start_voting(self, ctx: Context, duration: int = 24):
        """Start the voting phase after nominations (Admin only). Default duration is 24 hours."""

        # Check if voting is already active
        voting_active = db["voting_state"].find_one({"status": "active"})

        if voting_active:
            await ctx.send("❌ Voting is already active! Use `!start_voting_override` if needed.")
            return  # Prevent duplicate voting processes

        await self._start_voting_process(ctx, duration, override=False)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def start_voting_override(self, ctx: Context, duration: int = 24):
        """Force start a new voting phase, ignoring if one is already active (Admin only)."""

        await self._start_voting_process(ctx, duration, override=True)

    async def _start_voting_process(self, ctx: Context, duration: int, override: bool):
        """Handles the main voting process, with override support."""

        if override:
            print("⚠️ DEBUG: Override enabled - forcing voting start.")

        # Mark voting as active
        db["voting_state"].delete_many({})  # Remove any previous state
        db["voting_state"].insert_one({"status": "active"})

        nominations = list(nominations_collection.find())

        if not nominations:
            await ctx.send("No nominations to vote on!")
            db["voting_state"].delete_many({})
            return

        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            await ctx.send("❌ The `#ban_list` channel was not found.")
            return

        # Clear previous user nominations
        user_nominations_collection.delete_many({})
        top_players = sorted(nominations, key=lambda x: x["votes"], reverse=True)[:10]
        votes = {player["player_name"]: 0 for player in top_players}

        embed = Embed(
            title="🗳️ Parlay Ban List Voting",
            description="Click a button to vote for a player to be banned this week!",
            color=discord.Color.red()
        )
        message_content = "\n".join([f"**{i+1}.** {player['player_name']}" for i, player in enumerate(top_players)])
        embed.add_field(name="Candidates", value=message_content, inline=False)

        view = BanListVoting(top_players)
        poll_message = await channel.send(embed=embed, view=view)

        await ctx.send(f"Voting has started! Duration: {duration} seconds.")

        await asyncio.sleep(duration)

        nominations_collection.delete_many({})  # Clear only after voting ends

        await self.end_voting(ctx)

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
        
    async def end_voting(self, ctx: Context):
        """End the voting phase and finalize the ban list."""
        # Get the #ban_list channel
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            return

        # Get the current week number
        current_week = datetime.now(timezone.utc).isocalendar()[1]
        # Count votes directly from `user_votes`
        vote_counts = list(user_votes_collection.aggregate([
            {"$group": {"_id": "$voted_for", "count": {"$sum": 5}}},
            {"$sort": {"count": -1}},
            {"$limit": 3}
        ]))

        if not vote_counts:
            await channel.send("❌ No valid votes were recorded. No bans this week.")
            db["voting_state"].delete_many({})
            return

        # Create the final list of banned players
        ban_list = [{"player": vote["_id"], "votes": vote["count"]} for vote in vote_counts]
        # Store in `ban_list` collection
        ban_list_collection.insert_one({
            "week": f"Week {current_week}",
            "banned_players": ban_list
        })

        # Clear the votes collection (but keep nominations)
        user_votes_collection.delete_many({})

        # Format the message with inflated votes
        ban_list_message = "\n".join([f"🚫 {entry['player']} ({entry['votes']} votes)" for entry in ban_list])
        embed = Embed(
            title="🚨 Weekly Parlay Ban List",
            description=ban_list_message if ban_list_message else "No players received votes.",
            color=discord.Color.red()
        )

        # Send the embed with the ban list
        await channel.send(embed=embed)

        # Remove voting state
        db["voting_state"].delete_many({})

    @app_commands.command(name="show_banlist", description="View the banned players for a specific week.")
    async def show_banlist(self, interaction: Interaction, week: int = None):
        """Show the banned players for the requested week. Defaults to the current week if none is provided."""
        
        # Get the current week if no week is specified
        if week is None:
            week = datetime.now(timezone.utc).isocalendar()[1]

        week_str = f"Week {week}"
        ban_entry = ban_list_collection.find_one({"week": week_str})

        if not ban_entry or not ban_entry["banned_players"]:
            await interaction.response.send_message(f"No players were banned in {week_str}.")
            return
        
        ban_list_message = "\n".join([f"🚫 {player}" for player in ban_entry["banned_players"]])
        embed = Embed(title=f"🚨 {week_str} Parlay Ban List", description=ban_list_message, color=discord.Color.red())

        await interaction.response.send_message(embed=embed)