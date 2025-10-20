import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timedelta
from storage import get_user_data, update_user_data, load_data
from config import *
from math import floor

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_roulette = {}

    # ======= BALANCE =======
    @app_commands.command(name='bal', description="Check your or someone else's balance")
    async def bal(self, interaction: discord.Interaction, user: discord.User = None):
        user = user or interaction.user
        user_data = get_user_data(user.id)
        embed = discord.Embed(
            title=f"💰 Balance for {user.display_name}",
            description=f"Wallet: ${user_data['balance']:,}\nBank: ${user_data['bank']:,}\nNet Worth: ${user_data['balance'] + user_data['bank']:,}",
            color=0x0099ff
        )
        await interaction.response.send_message(embed=embed, ephemeral=(user != interaction.user))

    # ======= LEADERBOARD =======
    @app_commands.command(name='top', description='Show the richest users')
    async def top(self, interaction: discord.Interaction):
        data = load_data(ECONOMY_FILE)
        if not data:
            await interaction.response.send_message("No users found!", ephemeral=True)
            return
        leaderboard = sorted(data.items(), key=lambda item: item[1]['balance'] + item[1]['bank'], reverse=True)[:10]
        embed = discord.Embed(
            title="💸 Top 10 Richest Users",
            color=0xffd700
        )
        for idx, (user_id, user_data) in enumerate(leaderboard, 1):
            try:
                member = await self.bot.fetch_user(int(user_id))
                name = member.display_name
            except Exception:
                name = f"User {user_id}"
            net = user_data['balance'] + user_data['bank']
            embed.add_field(
                name=f"{idx}. {name}",
                value=f"Balance: ${user_data['balance']:,} | Bank: ${user_data['bank']:,} | Net: ${net:,}",
                inline=False
            )
        await interaction.response.send_message(embed=embed)

    # ======= ROB =======
    @app_commands.command(name='rob', description="Rob another user")
    async def rob(self, interaction: discord.Interaction, target: discord.User):
        if target.id == interaction.user.id:
            await interaction.response.send_message("You can't rob yourself!", ephemeral=True)
            return
        user_data = get_user_data(interaction.user.id)
        target_data = get_user_data(target.id)
        if user_data['balance'] < 100:
            await interaction.response.send_message("You need at least $100 in your wallet to rob someone!", ephemeral=True)
            return
        if target_data['balance'] < 100:
            await interaction.response.send_message(f"{target.display_name} doesn't have enough money to rob!", ephemeral=True)
            return
        if user_data.get('last_rob'):
            last_time = datetime.fromisoformat(user_data['last_rob'])
            if datetime.now() < last_time + timedelta(hours=1):
                next_time = last_time + timedelta(hours=1)
                await interaction.response.send_message(f"You can rob again <t:{int(next_time.timestamp())}:R>", ephemeral=True)
                return
        success = random.random() < 0.45
        if success:
            amount = random.randint(50, min(300, target_data['balance']))
            user_data['balance'] += amount
            target_data['balance'] -= amount
            result = f"💸 Success! You stole ${amount:,} from {target.display_name}!"
        else:
            amount = random.randint(25, min(200, user_data['balance']))
            user_data['balance'] -= amount
            result = f"🚨 You got caught! You paid ${amount:,} as a fine."
        user_data['last_rob'] = datetime.now().isoformat()
        update_user_data(interaction.user.id, user_data)
        update_user_data(target.id, target_data)
        await interaction.response.send_message(result)

    # ======= ROULETTE =======
    @app_commands.command(name="roulette", description="Bet at least $100 on red or black. Result in 30 seconds!")
    async def roulette(self, interaction: discord.Interaction, color: str, amount: int):
        color = color.lower()
        if color not in ("red", "black"):
            await interaction.response.send_message("You must choose `red` or `black`.", ephemeral=True)
            return
        if amount < 100:
            await interaction.response.send_message("Minimum bet is $100.", ephemeral=True)
            return
        user_data = get_user_data(interaction.user.id)
        if user_data['balance'] < amount:
            await interaction.response.send_message("You don't have enough money in your wallet!", ephemeral=True)
            return
        if interaction.user.id in self.active_roulette:
            await interaction.response.send_message("You already have an active roulette bet! Wait for it to finish.", ephemeral=True)
            return
        user_data['balance'] -= amount
        update_user_data(interaction.user.id, user_data)
        self.active_roulette[interaction.user.id] = (color, amount)
        embed = discord.Embed(
            title="🎰 Roulette",
            description=f"{interaction.user.display_name} bets **${amount:,}** on **{color.upper()}**!\n\nResult in 30 seconds...",
            color=0xd72631 if color == "red" else 0x111111
        )
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(30)
        winning_color = random.choice(["red", "black"])
        del self.active_roulette[interaction.user.id]
        if color == winning_color:
            user_data = get_user_data(interaction.user.id)
            winnings = amount * 2
            user_data['balance'] += winnings
            update_user_data(interaction.user.id, user_data)
            result_text = f"🎉 The ball has chosen **{winning_color.upper()}**!\nYou won **${winnings:,}**!"
        else:
            result_text = f"😢 The ball has chosen **{winning_color.upper()}**.\nYou lost your **${amount:,}** bet."
        await interaction.followup.send(result_text, ephemeral=True)

    # ======= ADMIN: ADD MONEY (role-based) =======
    @app_commands.command(name="add_money", description="Give money to a user (requires special role)")
    async def add_money(self, interaction: discord.Interaction, user: discord.User, amount: int):
        guild = interaction.guild
        member = guild.get_member(interaction.user.id)
        if not member:
            await interaction.response.send_message("Could not verify your role.", ephemeral=True)
            return
        if ADD_MONEY_ROLE_ID not in [role.id for role in member.roles]:
            await interaction.response.send_message(
                "You don't have permission to use this command.", ephemeral=True)
            return
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return
        user_data = get_user_data(user.id)
        user_data['balance'] += amount
        update_user_data(user.id, user_data)
        await interaction.response.send_message(
            f"Gave ${amount:,} to {user.display_name}. New balance: ${user_data['balance']:,}")

async def setup(bot):
    await bot.add_cog(Economy(bot))
