import discord
from discord.ext import commands
import logging
import os
from dotenv import load_dotenv
import asyncio


load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

async def main():
    await bot.load_extension('cogs.teams')
    await bot.load_extension('cogs.matches')
    await bot.start(token)

@bot.event
async def on_ready():
    print("Bot is ready!")

if __name__ == "__main__":
    asyncio.run(main())


