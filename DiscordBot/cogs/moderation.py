import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ext.commands import Cog
import re

from .channels.channel_ids import *
from .other.bad_words import bad_words

class ReasonModal(Modal):
    def __init__(self, action_type: str, target_member: discord.Member, embed_message: discord.Message):
        super().__init__(title=f"{action_type.title()} Reason", timeout=None)
        self.action_type = action_type
        self.target_member = target_member
        self.embed_message = embed_message

        self.reason = TextInput(
            label="Reason for action",
            placeholder=f"Enter the reason for the {action_type.lower()}...",
            required=True,
            max_length=200
        )
        self.add_item(self.reason)

        if action_type == "timeout":
            self.duration = TextInput(
                label="Timeout Duration (e.g. 10m, 1h, 2d)",
                placeholder="Use m = minutes, h = hours, d = days",
                required=True,
                max_length=10
            )
            self.add_item(self.duration)

    async def on_submit(self, interaction: Interaction):
        reason = self.reason.value
        description = self.embed_message.embeds[0].description if self.embed_message.embeds else ""
        match = re.search(r"Message: (.+)", description)
        offender_message = match.group(1).strip() if match else "N/A"

        offender = self.target_member

        if self.action_type =="ban":
            await self.target_member.ban(reason=reason)
            await interaction.response.send_message(f"🔨 {self.target_member} was **banned**.\n**Reason**: {reason}", ephemeral=True)

        elif self.action_type == "timeout":
            from datetime import timedelta

            duration_str = self.duration.value.strip().lower()
            time_mapping = {'m': 60, 'h': 3600, 'd': 86400}

            try:
                time_unit = duration_str[-1]
                time_value = int(duration_str[:-1])

                if time_unit in time_mapping:
                    total_seconds = time_value * time_mapping[time_unit]
                    duration = timedelta(seconds=total_seconds)
                    await self.target_member.timeout(duration, reason=reason)

                    await interaction.response.send_message(
                        f"⏳ {self.target_member} was **timed out** for `{duration_str}`.\n**Reason**: {reason}",
                        ephemeral=True
                    )
                else:
                    raise ValueError("Invalid unit")
            except Exception:
                await interaction.response.send_message(
                    "❌ Invalid timeout duration. Use formats like `10m`, `1h`, or `2d`.",
                    ephemeral=True
                )
                return
        await self.embed_message.delete()

        log_channel = interaction.guild.get_channel(logs_channel)
        await log_channel.send(
            f"🚨 **Moderation Action**: {self.action_type.title()}\n"
            f"👤 **Offender**: {offender.mention}\n"
            f"💬 **Message**: {offender_message}\n"
            f"🛠️ **By**: {interaction.user.mention}\n"
            f"📄 **Rule Broken**: {reason}"
        )

class ModerationView(View):
    def __init__(self, target_member: discord.Member, embed_message: discord.Message):
        super().__init__(timeout=None)
        self.target_member = target_member
        self.embed_message = embed_message

    @discord.ui.button(label="Ban", style=ButtonStyle.red)
    async def ban_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(ReasonModal("ban", self.target_member, self.embed_message))

    @discord.ui.button(label="Timeout", style=ButtonStyle.green)
    async def timeout_button(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(ReasonModal("timeout", self.target_member, self.embed_message))

    @discord.ui.button(label="Clear", style=ButtonStyle.gray)
    async def clear_button(self, interaction: Interaction, button: Button):
        await self.embed_message.delete()
        await interaction.response.send_message("🧹 Cleared moderation message.", ephemeral=True)

class ModerationCog(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id: int = logs_channel

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.id == member_join_channel:
            return
        
        if any(bad_word in message.content.lower() for bad_word in bad_words):
            await self.send_violation_log(message)

    async def send_violation_log(self, message):
        embed = Embed(
            title="Rule Violation",
            description=f"Offender: {message.author}\nMessage: {message.content}"
        )
        embed.add_field(name="Rule Broken", value="Inappropriate language used.")

        log_channel = message.guild.get_channel(logs_channel)
        sent_msg = await log_channel.send(embed=embed)

        view = ModerationView(target_member=message.author, embed_message=sent_msg)
        await sent_msg.edit(view=view)
