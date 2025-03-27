import discord
import difflib
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Context
from discord.ui import View, Button, Modal, TextInput

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
import asyncio
from datetime import datetime, timezone

from .roles.user_roles import *
from cogs.other.player_names import * 
from .channels.channel_ids import *

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

class NominateModal(Modal, title="Nominate Player"):
    name = TextInput(label="Player Nomination", placeholder="Enter a player to nominate here")

    async def on_submit(self, interaction: Interaction):
        max_nominations_per_user = 5
        nba_players = player_names

        matches = difflib.get_close_matches(self.name.value, nba_players, n=3, cutoff=0.6)

        user_id = interaction.user.id
        user_entry = user_nominations_collection.find_one({"user_id": user_id})

        if not user_entry:
            user_nominations_collection.insert_one({"user_id": user_id, "nominated_players": []})

        user_entry = user_nominations_collection.find_one({"user_id": user_id})
        if len(user_entry["nominated_players"]) >= max_nominations_per_user:
            await interaction.response.send_message("❌ You have reached your nomination limit (5).", ephemeral=True)
            return
        
        if matches:
            player_name = matches[0]
            await interaction.response.send_message(f"{player_name} has been nominated", delete_after=30)
        else:
            await interaction.response.send_message("learn to spell cuh", ephemeral=True)
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

class ParlayBan(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id: int = 1344374500271329320  # Ban list channel ID
        self.max_nominations_per_user = 5
        self.pre_poll_message_id: int = None
        self.poll_message_id: int = None
        self.nomination_message = None
        self.update_nominations.start()

    @app_commands.command(name="nominate", description="Nominate a player to be banned from parlays this week")
    async def nominate(self, interaction: Interaction, player_name: str):
        """Nominate a player to be banned from parlays this week."""
        
        voting_status = db["voting_state"].find_one({"status": "active"})
        if voting_status:
            await interaction.response.send_message("Nominations are closed. Voting is in progress.", delete_after=10)
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

        await interaction.response.send_message(f"✅ {player_name.title()} has been nominated!", delete_after=30)

    @tasks.loop(minutes=5)
    async def update_nominations(self):

        view = View(timeout=None)

        button = Button(label="Nominate A Player", style = ButtonStyle.primary)
        async def button_callback(interaction: Interaction):
            await interaction.response.send_modal(NominateModal())
        button.callback = button_callback

        view.add_item(button)

        channel = self.bot.get_channel(self.channel_id)
        voting_active = db["voting_state"].find_one({"status": "active"})
        if not channel:
            return
        if voting_active:
            return
        nominations = list(nominations_collection.find())
        top_players = sorted(nominations, key=lambda x: x["votes"], reverse=True)

        embed = Embed(
            title="🏆 Current Nominations",
            color=discord.Color.red()
        )

        if top_players:
            message_content = "\n".join([f"**{i+1}.** {player['player_name']} ({player['votes']} votes)" for i, player in enumerate(top_players)])
        else:
            message_content = "No players have been nominated yet. Be the first to nominate using the button below!"

        embed.add_field(name="Candidates", value=message_content, inline=False)

        if self.nomination_message:
            try:
                await self.nomination_message.delete()
            except discord.NotFound:
                print("⚠️ DEBUG: Old nominations message not found, sending new one.")

        # Send new message and store it
        self.nomination_message = await channel.send(embed=embed, view=view)

    @update_nominations.before_loop
    async def before_update_nominations(self):
        await self.bot.wait_until_ready()
    
    @app_commands.command(name="nominators", description="get the list of users who nominated")
    @app_commands.default_permissions(administrator=True)
    async def nominators(self, interaction: Interaction):
        users = user_nominations_collection.distinct("user_id")

        if not users:
            await interaction.response.send_message("No users have submitted nominations yet", ephemeral=True)
            return
        
        user_mentions = ", ".join(f"<@{user_id}>" for user_id in users)
        response_message = (
            "🎉 **NOMINATION REWARDS!** 🎉\n\n"
            "🏆 **All users who nominated are entered for a chance to win a** ***FREE 1-week VIP membership!*** 🏆\n"
            "👑 **Your nominations help shape the weekly ban list—thank you for participating!** 🙌\n\n"
            "🔹 **Users who nominated:**\n"
            f"{user_mentions}\n\n"
            f"🔥 **Want to enter?** Nominate now in <#{ban_list_channel}> before it's too late! "
        )
        await interaction.response.send_message(response_message, ephemeral=False)

    async def voters(self, channel: discord.TextChannel):
        users = user_votes_collection.distinct("voted_by")

        if not users:
            print("no users voted")
            return
        
        user_mentions = ", ".join(f"<@{user_id}>" for user_id in users)
        response_message = (
            "🗳️ **VOTING APPRECIATION** 🗳️\n\n"
            "🎉 **Huge thanks to everyone who cast their vote in this week's Parlay Ban List!** 🎉\n"
            "🙌 **Your input directly shapes the plays allowed each week — every vote counts!** 🙌\n\n"
            "📋 **Voters this week:**\n"
            f"{user_mentions}\n\n"
            f"🔥 **Want to be part of next week’s decision?** Make sure to vote in <#{ban_list_channel}> when voting opens!"
        )
        await channel.send(response_message)

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

        #delete the nomination leaderboard.

        if self.nomination_message:
            try:
                await self.nomination_message.delete()
            except discord.NotFound:
                print("⚠️ DEBUG: Old nominations message not found")

        if override:
            print("⚠️ DEBUG: Override enabled - forcing voting start.")

        # Mark voting as active
        db["voting_state"].delete_many({})  # Remove any previous state
        db["voting_state"].insert_one({"status": "active"})

        nominations = list(nominations_collection.find())

        if not nominations:
            await ctx.send("No nominations to vote on!", delete_after=5)
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


        #send message
        message ="""@everyone
# 🚨🚨 **PARLAY BAN LIST VOTING IS LIVE!** 🚨🚨
# 🔥 **It’s time to make your voice heard!** 🔥 
🔴 **Who deserves to be BANNED this week?** 🔴
🏆  **The nominations are in, and now it’s YOUR turn to decide!** Click a button below to cast your vote and influence the **official Parlay Ban List.** 🏆 

📜 **🔽 NOMINEES 🔽**  
*(See the embed below!)*  

⏳ **Voting closes soon—don’t miss your chance to make an impact!** ⏳

⚠️ **Every vote counts. Don’t let someone else decide for you!** ⚠️

💥 **VOTE NOW!** 💥
                    """
        pre_poll_message = await ctx.send(f"{message} ****Voting will be active for {duration} hours.**")
        self.pre_poll_message_id = pre_poll_message.id  # ✅ Correctly storing the message ID

        embed = Embed(
            title="🗳️ Parlay Ban List Voting",
            description="Click a button to vote for a player to be banned this week!",
            color=discord.Color.red()
        )
        message_content = "\n".join([f"**{i+1}.** {player['player_name']}" for i, player in enumerate(top_players)])
        embed.add_field(name="Candidates", value=message_content, inline=False)

        view = BanListVoting(top_players)
        poll_message = await channel.send(embed=embed, view=view)
        self.poll_message_id = poll_message.id  # Store only the message ID

        duration1 = duration*3600
        print(f"voting for {duration1} seconds")
        await asyncio.sleep(duration1)

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
        channel = self.bot.get_channel(self.channel_id)
        if not channel:
            return
        
        # Delete the pre-voting message if it exists
        if self.pre_poll_message_id:
            try:
                pre_poll_message = await channel.fetch_message(self.pre_poll_message_id)
                await pre_poll_message.delete()
                print("✅ DEBUG: Pre-voting message deleted successfully.")
            except discord.NotFound:
                print("⚠️ DEBUG: Pre-voting message not found, possibly already deleted.")
            self.pre_poll_message_id = None
        
        # Delete the poll message if it exists
        if self.poll_message_id:
            try:
                poll_message = await channel.fetch_message(self.poll_message_id)
                await poll_message.delete()
                print("✅ DEBUG: Voting message deleted successfully.")
            except discord.NotFound:
                print("⚠️ DEBUG: Voting message not found, possibly already deleted.")
            self.poll_message_id = None

        current_week = datetime.now(timezone.utc).isocalendar()[1]
        
        vote_counts = list(user_votes_collection.aggregate([
            {"$group": {"_id": "$voted_for", "count": {"$sum": 5}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))

        if not vote_counts:
            await channel.send("❌ No valid votes were recorded. No bans this week.")
            db["voting_state"].delete_many({})
            return

        ban_list = [{"player": vote["_id"], "votes": vote["count"]} for vote in vote_counts]
        ban_list_collection.insert_one({
            "week": f"Week {current_week}",
            "banned_players": ban_list
        })
        await self.voters(send_channel)
        user_votes_collection.delete_many({})

        banned_players = ban_list[:3]
        close_calls = ban_list[3:]

        embed = discord.Embed(
            title="🚨🚨 𝗪𝗘𝗘𝗞𝗟𝗬 𝗣𝗔𝗥𝗟𝗔𝗬 𝗕𝗔𝗡 𝗟𝗜𝗦𝗧 🚨🚨",
            description=(
                "📢 **@everyone**  ✨ **𝗧𝗛𝗘 𝗩𝗢𝗧𝗘𝗦 𝗔𝗥𝗘 𝗜𝗡!** ✨ 🗳️\n\n"
                "🔥 **The community has spoken, and these players are OFF the board this week!** 🔥\n\n"
                "⚠️ **Adjust your bets accordingly!** ⚠️"
            ),
            color=discord.Color.gold()
        )

        banned_text = "\n".join([f'🚫 **{entry["player"]}** — **{entry["votes"]} votes**' for entry in banned_players])
        embed.add_field(name="🚫 **𝗢𝗙𝗙𝗜𝗖𝗜𝗔𝗟𝗟𝗬 𝗕𝗔𝗡𝗡𝗘𝗗 (𝗧𝗢𝗣 𝟯)** 🚫", value=banned_text, inline=False)

        if close_calls:
            close_calls_text = "\n".join([f'**{"🔟" if (i+4) == 10 else str(i+4) + "️⃣"} {entry["player"]}** — **{entry["votes"]} votes**' for i, entry in enumerate(close_calls)])
            embed.add_field(name="📊 **𝗖𝗟𝗢𝗦𝗘 𝗖𝗔𝗟𝗟𝗦 (𝗡𝗲𝗮𝗿𝗹𝘆 𝗕𝗮𝗻𝗻𝗲𝗱, 𝗕𝘂𝘁 𝗦𝘂𝗿𝘃𝗶𝘃𝗲𝗱)** 📊", value=close_calls_text, inline=False)

        embed.set_footer(text="🗳️ 𝗠𝗮𝗸𝗲 𝘆𝗼𝘂𝗿 𝘃𝗼𝗶𝗰𝗲 𝗵𝗲𝗮𝗿𝗱 𝗶𝗻 𝗻𝗲𝘅𝘁 𝘄𝗲𝗲𝗸'𝘀 𝘃𝗼𝘁𝗲! 𝗗𝗼𝗻'𝘁 𝗺𝗶𝘀𝘀 𝗼𝘂𝘁!")

        await channel.send(content="@everyone", embed=embed)

        db["voting_state"].delete_many({})
        send_channel = self.bot.get_channel(announcements_channel)
        await asyncio.sleep(5)
        await self.update_nominations()

    @app_commands.command(name="show_banlist", description="View the banned players for a specific week.")
    async def show_banlist(self, interaction: Interaction, week: int = None):
        """Show the banned players for the requested week. Defaults to the current week if none is provided."""
        if week is None:
            week = datetime.now(timezone.utc).isocalendar()[1]
        week_str = f"Week {week}"
        ban_entry = ban_list_collection.find_one({"week": week_str})

        if not ban_entry or not ban_entry["banned_players"]:
            await interaction.response.send_message(f"No players were banned in {week_str}.", delete_after= 30)
            return

        banned_text = "\n".join([f'🚫 {entry["player"]} ({entry["votes"]} votes)' for entry in ban_entry["banned_players"][:3]])
        close_calls_text = "\n".join([f'**{["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][i]} {entry["player"]}** — {entry["votes"]} votes' for i, entry in enumerate(ban_entry["banned_players"][3:])])

        embed = Embed(
            title=f"🚨 {week_str} Parlay Ban List",
            color=discord.Color.red()
        )
        embed.add_field(name="🚫 Officially Banned (Top 3) 🚫", value=banned_text, inline=False)
        if close_calls_text:
            embed.add_field(name="📊 Close Calls (Nearly Banned, But Survived) 📊", value=close_calls_text, inline=False)

        await interaction.response.send_message(embed=embed, delete_after=30)
