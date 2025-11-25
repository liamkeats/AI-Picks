import os
from urllib.parse import quote_plus
import io

import discord
from discord import File
from discord import Interaction
from discord import app_commands
from discord.ext import commands
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

from datetime import datetime, timedelta, timezone
from collections import defaultdict

# === Load Environment Variables ===
load_dotenv("token.env")
BOT_TOKEN = os.getenv("TOKEN")

# MongoDB setup with password from .env
PASSWORD = quote_plus(str(os.getenv('MONGO_PASSWORD')))
uri = f"mongodb+srv://keatsliam:{PASSWORD}@aipicks.cdvhr.mongodb.net/?retryWrites=true&w=majority&appName=AiPicks"
client = MongoClient(uri, server_api=ServerApi('1'))
db = client["AI_Picks_Bot"]
giveaway_collection = db["giveaway_entries"]

# === Bot Setup ===
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix="&", intents=intents)

# === Configuration ===
WATCH_CHANNEL_ID = 1312907177882554501  # Change to your submission channel
MOD_REVIEW_CHANNEL_ID = 1357914530109325534  # Change to your mod review channel

# === Button View ===
class GiveawayReviewView(discord.ui.View):
    def __init__(self, user_id, message_content):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.message_content = message_content

    @discord.ui.button(label="✅ Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(self.user_id)
        giveaway_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"tally": 1}, "$setOnInsert": {"user_id": user_id}},
            upsert=True
        )
        await interaction.response.edit_message(content=f"✅ Approved <@{self.user_id}>", view=None)
        await interaction.message.delete(delay=3)  # <-- Auto delete after 3 seconds

    @discord.ui.button(label="❌ Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content=f"❌ Rejected <@{self.user_id}>", view=None)
        await interaction.message.delete(delay=3)  # <-- Auto delete after 3 seconds


# === Events ===
@bot.event
async def on_message(message):
    if message.author.bot or message.channel.id != WATCH_CHANNEL_ID:
        return

    mod_channel = bot.get_channel(MOD_REVIEW_CHANNEL_ID)
    if not mod_channel:
        print("❗ Mod channel not found.")
        return

    # Send one mod message for each image
    for attachment in message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            embed = discord.Embed(
                title="New Image Submission",
                description=f"From <@{message.author.id}>",
                color=discord.Color.blurple()
            )
            embed.set_image(url=attachment.url)

            view = GiveawayReviewView(user_id=message.author.id, message_content="[Image]")

            await mod_channel.send(embed=embed, view=view)

    # Optional: Also show message text once if there's any
    if message.content:
        embed = discord.Embed(
            title="Message Content",
            description=message.content,
            color=discord.Color.dark_gray()
        )
        await mod_channel.send(content=f"From <@{message.author.id}>", embed=embed)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Bot is ready! Logged in as {bot.user} (ID: {bot.user.id})")

# === Commands ===
@bot.tree.command(name="giveaway_thanks", description="Thank everyone who entered the giveaway")
async def giveaway_thanks(interaction: Interaction):
    await interaction.response.defer()  # 👈 prevents interaction timeout

    entries = giveaway_collection.find({})
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

    # Header message
    header = (
        "🎁 **GIVEAWAY ENTRIES LOCKED IN!** 🎁\n\n"
        "💰 Everyone below has secured their spot for our current giveaway!\n"
        "🔥 Thank you all for jumping in — good luck when we spin that wheel! 🎡\n\n"
        "🔹 **Entrants:**\n"
    )

    # Chunk handling
    chunks = []
    current_chunk = header
    for mention in mentions:
        if len(current_chunk) + len(mention) + 2 > 2000:
            chunks.append(current_chunk.strip())
            current_chunk = mention + ", "
        else:
            current_chunk += mention + ", "
    chunks.append(current_chunk.strip())

    # Send the first chunk as followup, rest as regular messages
    await interaction.followup.send(chunks[0])
    for chunk in chunks[1:]:
        await interaction.channel.send(chunk)



@bot.tree.command(name="export_giveaway", description="Export a .txt file of all giveaway entries (admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def export_giveaway(interaction: Interaction):
    print("🔁 /export_giveaway triggered")

    entries = giveaway_collection.find({})
    name_list = []

    for entry in entries:
        print(f"📦 DB Entry: {entry}")
        user_id = int(entry["user_id"])
        tally = entry.get("tally", 0)

        try:
            user = await interaction.guild.fetch_member(user_id)
            if user:
                print(f"✅ Adding {user.name} x{tally}")
                name_list.extend([user.display_name] * tally)
        except Exception as e:
            print(f"⚠️ Failed to fetch user {user_id}: {e}")

    if not name_list:
        await interaction.response.send_message("❌ No entries to export.", ephemeral=True)
        return

    content = "\n".join(name_list)
    file = File(io.BytesIO(content.encode()), filename="giveaway_names.txt")
    await interaction.response.send_message("🎯 Here's your giveaway name list:", file=file, ephemeral=True)
    print("📤 File sent!")

# === Optional Tally Command ===
@bot.command()
async def tally(ctx, user: discord.Member = None):
    user = user or ctx.author
    entry = giveaway_collection.find_one({"user_id": str(user.id)})
    count = entry["tally"] if entry else 0
    await ctx.send(f"🎁 {user.mention} has **{count}** approved submissions.")

# === Start Bot ===
bot.run(BOT_TOKEN)
