import discord
from discord.ext.commands import Cog, Bot, Context
from discord.ext import commands

from .channels.channel_ids import *
class EmbedsCog(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        super().__init__()

    @commands.command()
    @commands.has_permissions(administrator = True)
    async def thirty(self, ctx: Context):
        # Create an embed message
        embed = discord.Embed(
            title="Free VIP with these 2 Steps! 🚀",
            description=(
                "**First Things First💯**\n"
                "Click one of the apps linked below and make a NEW account **USING PROMO CODE: AIPICKS**\n\n"
                "**BEST CHOICES:**\n"
                f"**<#{vivid_channel}>** - Get up to $1000 in bonus cash!\n"
                f"**<#{chalkboard_channel}>** - 100% deposit match up to $250\n"
                f"**<#{underdog_channel}>** - $100 deposit match & $25 sweat free bet \n\n"
                "**SOME OTHER APPS**\n"
                f"**<#{bet_channel}>** - Compete to make the best parlay! $250 Deposit Bonus\n"
                f"**<#{dabble_channel}>** - Get $10 FREE with no deposit\n"
                f"**<#{wannaparlay_channel}>** - 100% Deposit Match up to $200 & Injury Protection\n"
                "---\n\n"
                "**Second Step!💪**\n"
                f"**Deposit $10 or more** (use code: AIPICKS) and send a screenshot to us in <#{support_channel}> to claim your month of VIP\n\n"
                "**Disclaimer: Each app that you sign up for grants you 30 STACKABLE days of VIP Access! There's no limit to how many apps you can sign up for (3 Apps = 90 Days)**"
            ),
            color=discord.Color.green()  # Set embed color to green
        )
        embed.set_footer(text="AI Picks | Numbers Don't Lie")  # Footer for the embed

        # Send the embed message to the same channel the command was invoked in
        await ctx.send(embed=embed)

    # a welcome command to send to whichever channel
    @commands.command()
    @commands.has_permissions(administrator = True)
    async def welcome(self, ctx: Context):
        # Create an embed message
        embed = discord.Embed(
            title="Welcome to AI Picks Discord 🎉",
            description=(
                "**Check out this video to join VIP for 30 Days Completely FREE! 👉 (video)**\n\n"
                f"✅ FREE PICKS : 1-2 free picks/day are posted in <#{free_picks_channel}> \n\n"
                f"🏆 VIP COMMUNITY: ALL plays are posted in <#{vip_plays_channel}>\n\n"
                f"💰 Join VIP for 30 Days FREE or Extend your plan here<#{free_vip_channel}>\n\n"
                f"🤝 Contact Us: <#{support_channel}>"
            ),
            color=discord.Color.green()  # Set embed color to green
        )
        embed.set_footer(text="AI Picks | Numbers Don't Lie")  # Footer for the embed

        # Send the embed message to the same channel the command was invoked in
        await ctx.send(embed=embed)
