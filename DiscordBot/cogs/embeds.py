import discord
from discord import Embed, Color
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
        embed = Embed(
            title="Free VIP with these 2 Steps! 🚀",
            description=(
                "**First Things First💯**\n"
                "Click one of the apps linked below and make a NEW account **USING PROMO CODE: AIPICKS**\n\n"
                "**BEST CHOICES:**\n"
                f"**<#{sleeper_channel}>** - Play $5, get $55 Instantly!\n"
                f"**<#{chalkboard_channel}>** - $100 deposit match & $25 sweat free bet\n"
                f"**<#{underdog_channel}>** - Get up to $1000 in FREE bonus cash!\n\n"
                "**SOME OTHER APPS**\n"
                f"**<#{bet_channel}>** - 100% Deposit Match up to $200 & Injury Protection\n"
                f"**<#{dabble_channel}>** - Get $25 FREE with no deposit\n"
                f"**<#{wannaparlay_channel}>** - Compete to make the best parlay! $250 Deposit Bonus\n"
                "---\n\n"
                "**Second Step!💪**\n"
                f"**Deposit $10 or more** (use code: AIPICKS) and send a screenshot to us in <#{support_channel}> to claim your month of VIP\n\n"
                "**Disclaimer: Each app that you sign up for grants you 30 STACKABLE days of VIP Access! There's no limit to how many apps you can sign up for (3 Apps = 90 Days)**"
            ),
            color=Color.green()  # Set embed color to green
        )
        embed.set_footer(text="AI Picks | Numbers Don't Lie")  # Footer for the embed

        # Send the embed message to the same channel the command was invoked in
        await ctx.send(embed=embed)

    # a welcome command to send to whichever channel
    @commands.command()
    @commands.has_permissions(administrator = True)
    async def welcome(self, ctx: Context):
        # Create an embed message
        embed = Embed(
            title="**Welcome to AI Picks Discord 🎉**",
            description=(
                "**Check out this video to join VIP for 30 Days Completely FREE! 👉 https://discord.com/channels/1309493151102271488/1312451356400812103/1348157464536678493**\n\n"
                f"✅ FREE PICKS : 1-2 free picks/day are posted in <#{free_picks_channel}> \n\n"
                f"🏆 VIP COMMUNITY: ALL plays are posted in <#{vip_plays_channel}>\n\n"
                f"💰 Join VIP for 30 Days FREE or Extend your plan here<#{free_vip_channel}>\n\n"
                f"🤝 Contact Us: <#{support_channel}>"
            ),
            color=Color.green()  # Set embed color to green
        )
        embed.set_footer(text="AI Picks | Numbers Don't Lie")  # Footer for the embed

        # Send the embed message to the same channel the command was invoked in
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator = True)
    async def rules(self, ctx: Context):

        embed = Embed(
            title=None,
            description=(
                "# Welcome to AI PICKS\n\n"
                "By joining the AI Picks server, you agree to comply with the following Rules, Terms of Service and acknowledge that you have read and understood the disclaimer. Any breach of the disclaimer, rules, or TOS may result in a warning or ban."
                "\n\n"
                "## __***Rules, TOS, and Disclaimer:***__\n\n"
                "- This server is restricted to individuals who are 18 years or older. Any underage members will be banned immediately.\n\n"
                "- Do not share links to other Discord servers or promote competitors. Do not promote any of your codes. Do not ask members to DM you.\n\n"
                "- The server is designed for educational purposes, AI Picks is not liable for any financial losses incurred from gambling decisions made by members. All wagering choices are to be made at your own discretion.\n\n"
                "- Please conduct yout own thorough reaearch and due diligence before making any decisions. The posts and information shared here are not recommendations to buy or sell securities or to place any bets.\n\n"
                "- You are soley responsible for your own investment and gambling choices. We are not financial advisors, and all trading and wagering decisions are made at your own discretion.\n\n"
                "- No information privided in this discord server should be seen as a guarentee of any specific outcome or result.\n\n"
                "- All members are required to adhere to Discord's Terms of Service. ( Terms of Service | Discord )  and Guidelines ( Community Guidelines | Discord )\n\n"
                "- Please treat the server and all members with respect in the chat.\n\n"
                "- There is to be no discriminitory, bigotry, or hateful speech within the discord server.\n\n"
            ),
            color=Color.green()
        )
        embed.set_footer(text="AI Picks | Numbers Don't Lie")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator = True)
    async def join_vip(self, ctx: Context):

        embed = Embed(
            title="**Are You Ready To Become A Winning Sports Bettor With Our Analysts?💰**",
            description=(
                "**\n📢 WHAT’S INCLUDED IN VIP? 📢**\n\n"
                f"**🔥 All Expert Picks →** Get access to every slip posted in <#{vip_plays_channel}>, covering PrizePicks, Sleeper, Underdog, Vivid, and more!\n\n"
                "**💬 Exclusive Community Access →** Join our **active betting community**, where members share their own winning slips, discuss plays, and sweat out bets together like a real **betting team.**\n\n"
                "**🎁 Exclusive Giveaways & Content →** VIP members get access to **giveaways, premium tools, and betting insights** not available to anyone else.\n\n"
                "**📞 1-on-1 Support →** Need help with plays, bankroll management, or strategy? Get direct access to experienced bettors for guidance.\n\n"
                "**💰 Maximize Your Edge →** Gain **higher-value picks, better discussions, and exclusive betting advantages** to help you win more!\n\n"
                "**🚀 Upgrade Now & Join the Team!\n\n**"
                "[**🔥CLICK HERE TO JOIN**](https://www.winible.com/aipicks) 🔗"
            ),
            color=Color.green()
        )
        embed.set_footer(text="AI Picks | Numbers Don't Lie")

        await ctx.send(embed=embed)
        
