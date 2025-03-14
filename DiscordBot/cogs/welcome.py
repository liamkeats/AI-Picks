import discord
from discord.ext import commands
from discord.ext.commands import Cog, Context
from discord import app_commands, Interaction, Embed, ButtonStyle

from .roles.user_roles import *
from .channels.channel_ids import *

class Welcome(Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        free_role = guild.get_role(FREE_ROLE_ID)
        welcome_channel = guild.get_channel(member_join_channel)

        role_assigned = False
        dm_sent = False

        # Create an energetic embed message
        embed = discord.Embed(
            title=f"🎉 WELCOME TO {guild.name}! 🎉",
            description=f"Hey {member.mention}, we're so excited to have you here! 🚀✨\n\n"
                        "Get started in <#1334348131390984304> and check out what you can do:",
            color=discord.Color.green()
        )
        embed.add_field(
            name="🌟 Get Free VIP Access!",
            value=f"Go to <#1312451356400812103> to claim your **FREE VIP**! 🎁",
            inline=False
        )
        embed.add_field(
            name="📈 Free Picks Channel",
            value=f"Check out <#1312448620162715830> for **free betting picks**! 🏆",
            inline=False
        )
        embed.add_field(
            name="💬 Chat with the Community",
            value=f"Hang out in <#1310952414689361961> until you get VIP! 🗣️",
            inline=False
        )
        embed.add_field(
            name="🚫 Nominate Players for Ban List",
            value=f"Use <#1344374500271329320> to **nominate players** for the ban list! ⛔",
            inline=False
        )
        embed.set_footer(text="Enjoy your stay and good luck! 🍀")
        if free_role:
            await member.add_roles(free_role)
            role_assigned = True

        try:
            await member.send(embed=embed)
            dm_sent = True
        except discord.Forbidden:
            pass

        if welcome_channel:
            await welcome_channel.send(
                f"User: {member.mention} joined the server.\n"
                f"- Role assigned: {'✅' if role_assigned else '❌'}\n"
                f"- DM sent: {'✅' if dm_sent else '❌'}"
            )