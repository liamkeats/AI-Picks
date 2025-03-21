import discord
import difflib
from discord.ext.commands import Cog, Context
from discord.ui import View, Button, TextInput, Modal
from discord.ext import commands
from discord import Embed, ButtonStyle, Interaction

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv("token.env")
PASSWORD = os.getenv('MONGO_PASSWORD')
PASSWORD = quote_plus(PASSWORD)

uri = f"mongodb+srv://keatsliam:{PASSWORD}@aipicks.cdvhr.mongodb.net/?retryWrites=true&w=majority&appName=AiPicks"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["AI_Picks_Bot"]
testing_user_nominations_collection = db["testing"]
testing_nominations_collection = db["testing2"]

from cogs.other.player_names import *
nba_players = player_names

class TestModal(Modal, title="Nominate Player"):
    name = TextInput(label="Player Nomination", placeholder="Enter a player name here")


    async def on_submit(self, interaction: Interaction):
        max_nominations_per_user = 5
        print(f"user name: {interaction.user} and their id: {interaction.user.id}")

        matches = difflib.get_close_matches(self.name.value, nba_players, n=3, cutoff=0.6)
        
        
        user_id = interaction.user.id
        user_entry = testing_user_nominations_collection.find_one({"user_id": user_id})

        if not user_entry:
            testing_user_nominations_collection.insert_one({"user_id": user_id, "nominated_players": []})

        user_entry = testing_user_nominations_collection.find_one({"user_id": user_id})
        if len(user_entry["nominated_players"]) >= max_nominations_per_user:
            await interaction.response.send_message("❌ You have reached your nomination limit (5).", ephemeral=True)
            return
        
        if matches:
            player_name = matches[0]
            await interaction.response.send_message(f"{player_name} has been nominated")
        else:
            await interaction.response.send_message("learn to spell cuh")
            return

        player_entry = testing_nominations_collection.find_one({"player_name": player_name})
        if player_entry:
            testing_nominations_collection.update_one(
                {"player_name": player_name},
                {"$inc": {"votes": 1}, "$addToSet": {"nominated_by": user_id}}
            )
        else:
            testing_nominations_collection.insert_one({
                "player_name": player_name,
                "nominated_by": [user_id],
                "votes": 1
            })
        testing_user_nominations_collection.update_one(
            {"user_id": user_id},
            {"$push": {"nominated_players": player_name}}
        )




class TestingCog(Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def testing(self, ctx: Context):
        view = View(timeout=None)

        button = Button(label="testing button", style= ButtonStyle.primary)
        async def button_callback(interaction: Interaction):
            await interaction.response.send_modal(TestModal())
        button.callback = button_callback

        embed = Embed(
            title="testing",
            color=discord.Color.red(),
            description=("this is a test")
        )

        view.add_item(button)
        await ctx.send(embed=embed, view=view)