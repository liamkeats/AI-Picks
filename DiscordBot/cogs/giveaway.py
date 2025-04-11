import discord
from discord.ext import commands
from discord import app_commands, File, Interaction
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import io
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus

dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'token.env')
load_dotenv(dotenv_path)

# === MongoDB Connection Setup ===
PASSWORD = os.getenv('MONGO_PASSWORD')
if not PASSWORD:
    raise ValueError("MONGO_PASSWORD environment variable not set")
PASSWORD = quote_plus(str(PASSWORD))

MONGO_URI = os.getenv("MONGO_URL")
if not MONGO_URI:
    MONGO_URI = f"mongodb+srv://keatsliam:{PASSWORD}@aipicks.cdvhr.mongodb.net/?retryWrites=true&w=majority&appName=AiPicks"

client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
db = client["AI_Picks_Bot"]
giveaway_collection = db["giveaway_entries"]

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.watch_channel_id = 1312907177882554501
        self.mod_review_channel_id = 1357914530109325534
        self.giveaway_collection = giveaway_collection  # 👈 Fix here

    class GiveawayReviewView(discord.ui.View):
        def __init__(self, user_id, message_content, collection):
            super().__init__(timeout=None)
            self.user_id = user_id
            self.message_content = message_content
            self.collection = giveaway_collection

        @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green)
        async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
            user_id = str(self.user_id)
            self.collection.update_one(
                {"user_id": user_id},
                {"$inc": {"tally": 1}, "$setOnInsert": {"user_id": user_id}},
                upsert=True
            )
            await interaction.response.edit_message(content=f"✅ Approved <@{self.user_id}>", view=None)
            await interaction.message.delete(delay=3)

        @discord.ui.button(label="❌ Reject", style=discord.ButtonStyle.red)
        async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(content=f"❌ Rejected <@{self.user_id}>", view=None)
            await interaction.message.delete(delay=3)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.id != self.watch_channel_id:
            return

        mod_channel = self.bot.get_channel(self.mod_review_channel_id)
        if not mod_channel:
            print("❗ Mod channel not found.")
            return

        has_image = False

        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                has_image = True
                embed = discord.Embed(
                    title="New Image Submission",
                    description=f"From <@{message.author.id}>",
                    color=discord.Color.blurple()
                )
                embed.set_image(url=attachment.url)

                view = self.GiveawayReviewView(
                    user_id=message.author.id,
                    message_content="[Image]",
                    collection=self.giveaway_collection
                )
                await mod_channel.send(embed=embed, view=view)

        # Handle text-only messages OR include text separately if no image matched
        if message.content and not has_image:
            embed = discord.Embed(
                title="Message Submission",
                description=message.content,
                color=discord.Color.dark_gray()
            )

            view = self.GiveawayReviewView(
                user_id=message.author.id,
                message_content=message.content,
                collection=self.giveaway_collection
            )
            await mod_channel.send(content=f"From <@{message.author.id}>", embed=embed, view=view)


    @app_commands.command(name="giveaway_thanks", description="Thank everyone who entered the giveaway")
    async def giveaway_thanks(self, interaction: Interaction):
        await interaction.response.defer()

        entries = self.giveaway_collection.find({})
        mentions = []

        for entry in entries:
            user_id = int(entry["user_id"])
            try:
                user = await interaction.guild.fetch_member(user_id)
                if user:
                    mentions.append(user.mention)
            except:
                continue

        if not mentions:
            await interaction.followup.send("No entries found yet.", ephemeral=True)
            return

        header = (
            "🎁 **GIVEAWAY ENTRIES LOCKED IN!** 🎁\n\n"
            "💰 Everyone below has secured their spot for our current giveaway!\n"
            "🔥 Thank you all for jumping in — good luck when we spin that wheel! 🎡\n\n"
            "🔹 **Entrants:**\n"
        )

        chunks = []
        current_chunk = header
        for mention in mentions:
            if len(current_chunk) + len(mention) + 2 > 2000:
                chunks.append(current_chunk.strip())
                current_chunk = mention + ", "
            else:
                current_chunk += mention + ", "
        chunks.append(current_chunk.strip())

        await interaction.followup.send(chunks[0])
        for chunk in chunks[1:]:
            await interaction.channel.send(chunk)

    @app_commands.command(name="export_giveaway", description="Export a .txt file of all giveaway entries (admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def export_giveaway(self, interaction: Interaction):
        print("🔁 /export_giveaway triggered")
        await interaction.response.defer(ephemeral=True)  # 👈 prevents timeout!

        entries = self.giveaway_collection.find({})
        name_list = []

        for entry in entries:
            print(f"📦 DB Entry: {entry}")
            user_id = int(entry["user_id"])
            tally = entry.get("tally", 0)

            try:
                user = await interaction.guild.fetch_member(user_id)
                if user:
                    print(f"✅ Adding {user.display_name} x{tally}")
                    name_list.extend([user.display_name] * tally)
            except Exception as e:
                print(f"⚠️ Failed to fetch user {user_id}: {e}")

        if not name_list:
            await interaction.followup.send("❌ No entries to export.", ephemeral=True)
            return

        content = "\n".join(name_list)
        file = File(io.BytesIO(content.encode()), filename="giveaway_names.txt")
        await interaction.followup.send("🎯 Here's your giveaway name list:", file=file)
        print("📤 File sent!")

