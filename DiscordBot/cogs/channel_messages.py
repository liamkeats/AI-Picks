from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context
from discord import app_commands, Interaction, Embed, Color
from .other.stream_links import *


class ChannelMessagesCog(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        super().__init__()

    # hello command to check if bot is running
    @commands.command()
    async def hello(self, ctx: Context):
        await ctx.send("Hello! I am alive and running.")

    #command for users to find stream links
    @app_commands.command(name="findstream", description="This command shows available streaming links to watch games at your convinience")
    async def findstream(self, interaction:Interaction):
        # Multi-line string for links
        links_message = "\n".join(links)
        # Send the message with code formatting to clean up the output
        await interaction.response.send_message(f"Available streaming links:\n{links_message}")
    
    @app_commands.command(name= "devig", description="devig the odds of a match")
    async def devig(self, interaction: Interaction, bet_odds: int, devig_odds: int):
        if bet_odds < 0:
            p_bet = round(abs(bet_odds) / (abs(bet_odds) + 100), 4)
            payout = round(100 / abs(bet_odds), 4)
        else:
            p_bet = round(100 / (100 + bet_odds), 4)
            payout = round(bet_odds / 100, 4)
        
        if devig_odds < 0:
            p_win = round(abs(devig_odds) / (abs(devig_odds) + 100), 4)
        else:
            p_win = round(100 / (100 + devig_odds), 4)
        
        p_loss = round(1 - p_win, 4)
        ev = round(((p_win * payout) - (p_loss * 1)) * 100, 2)
        
        # Kelly Criterion (Full, Half, Quarter, Eighth)
        kelly_full = round((ev / 100) / payout * 100, 2)
        kelly_half = round(kelly_full / 2, 2)
        kelly_quarter = round(kelly_full / 4, 2)
        kelly_eighth = round(kelly_full / 8, 2)

        embed = Embed(
            title="Devig",
            description=(
                "EV coming right up\n"
                f"**EV**\n{ev}%\n\n"
                "**Full/Half/Quarter/Eighth Kelly**\n"
                f"{kelly_full} / {kelly_half} / {kelly_quarter} / {kelly_eighth}\n\n"
                f"**Bet Odds**\n{bet_odds}\n\n"
                f"**Fair Value**\n{devig_odds}\n\n"
                "**Courtesy of Mizzy The EV GOD**"
            ),
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed)
    