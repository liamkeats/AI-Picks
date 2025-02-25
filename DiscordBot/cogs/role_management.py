import discord
from discord import utils, Interaction, app_commands, ButtonStyle

from discord.ext import commands
from discord.ext.commands import Context
from discord.ui import Button, View
from discord.ext.commands import Cog, Bot

from .roles.bettor_app_roles import role_emoji_map
from .roles.user_roles import *
from .channels.channel_ids import *

class AppBettingButtons(View):
    def __init__(self):
        super().__init__(timeout=None)  # View does not time out
        for role_name, emoji in role_emoji_map.items():
            button = Button(
                label=role_name,
                style=ButtonStyle.primary,
                emoji=emoji,
                custom_id=f"{role_name.lower()}_button"
            )
            button.callback = self.role_button_callback  # Assign callback for each button
            self.add_item(button)

    async def role_button_callback(self, interaction: Interaction):
        """Handle the button click event."""
        role_name = interaction.data['custom_id'].split('_')[0].title()  # Extract role name from custom_id
        role = utils.get(interaction.guild.roles, name=role_name)

        if role:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"Removed the {role_name} role!", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"Added the {role_name} role!", ephemeral=True)
        else:
            await interaction.response.send_message(f"Role `{role_name}` not found.", ephemeral=True)

class RoleManagementCog(Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        super().__init__()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def reactionbuttons(self, ctx):
        await ctx.send("Select the apps you use the most", view=AppBettingButtons())
        
    @reactionbuttons.error
    async def reactionbuttons_error(self, ctx, error):
        """Handles errors for the reactionbuttons command."""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You do not have permission to use this command.", delete_after=5)

    @app_commands.command(name="check_roles", description="A command to check roles and make sure no VIP member also has the Free role.")
    @app_commands.default_permissions(administrator=True)
    async def check_roles(self, interaction:Interaction):
        changes_made = False
        channel = self.bot.get_channel(LOG_CHANNEL_ID)

        if channel is None:
            await interaction.response.send_message("Log channel not found!")
            return
        
        for guild in self.bot.guilds:
            for member in guild.members:
                vip_role = utils.get(guild.roles, id=VIP_ROLE_ID)
                free_role = utils.get(guild.roles, id=FREE_ROLE_ID)

                if vip_role and free_role:
                    if vip_role in member.roles and free_role in member.roles:
                        await member.remove_roles(free_role)
                        await channel.send(f"Removed 'Free' role from {member.mention} because they have VIP.")
                        changes_made = True  # Mark that changes were made

                    if vip_role not in member.roles and free_role not in member.roles:
                        await member.add_roles(free_role)
                        await channel.send(f"Added 'Free' role to {member.mention} because they don't have VIP.")
                        changes_made = True  # Mark that changes were made

        if not changes_made:
            await channel.send("All roles are correct. No changes made.")

        await interaction.response.send_message("Role check complete!")
    
    @commands.command()
    @commands.has_permissions(administrator=True)  # Restrict to users with Admin permissions
    async def nash_lover(self, ctx: Context):
        # Create a view to hold the buttons
        view = View(timeout=None)
        # Create buttons for each role and add them to the view
        button = Button(label="GET THE NASH ROLE", style=ButtonStyle.primary, emoji="👍")

        async def button_callback(interaction, role_name="NASH LOVER"):
            # Get the role
            role = discord.utils.get(interaction.guild.roles, name="NASH LOVER")

            if role:
                # Toggle the role - if the user already has the role, remove it; otherwise, add it
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role)
                    await interaction.response.send_message(f"Removed the {role.name} role!", ephemeral=True)
                else:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message(f"Added the {role.name} role!", ephemeral=True)
            else:
                await interaction.response.send_message(f"Role `{role_name}` not found.", ephemeral=True)

        button.callback = button_callback
        view.add_item(button)

        # Send the message with the buttons to the user's DM
        await ctx.send("React with a thumbs-up to get the NASH LOVER role!", view=view)
