import discord
from discord.ext import commands
from config import TOKEN

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=None, intents=intents)  # No prefix

async def load_cogs():
    await bot.load_extension("economy")
    await bot.load_extension("business")

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in!')
    try:
        await bot.tree.sync()
        print('Slash commands synced.')
    except Exception as e:
        print(f'Failed to sync slash commands: {e}')

async def main():
    await load_cogs()
    await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
