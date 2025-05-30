import discord
from discord.ext import commands
import logging 
from dotenv import load_dotenv
import os
import csv  

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print("Bot is ready!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!")

# Command to report match results.
@bot.command()
async def report_match(ctx, team_name: str, opponent_team_name: str, team_score: int, opponent_score: int):
    try:
        # Validate that scores are integers and non-negative
        if team_score < 0 or opponent_score < 0:
            await ctx.send("Scores must be non-negative integers.")
            return

        # Validate that team names are not empty
        if not team_name.strip() or not opponent_team_name.strip():
            await ctx.send("Team names cannot be empty.")
            return

        # Validate that the teams are not the same
        if team_name == opponent_team_name:
            await ctx.send("You cannot report a match against the same team.")
            return
        
        if team_score == opponent_score:
            await ctx.send("Match cannot be reported as a draw.")
            return
        
        # Determine the winner and loser
        if team_score > opponent_score:
            winner = team_name
            loser = opponent_team_name
        else:
            winner = opponent_team_name
            loser = team_name

        match_result = {
            "team_name": team_name,
            "opponent_team_name": opponent_team_name,
            "team_score": team_score,
            "opponent_score": opponent_score,
            "winner": winner,
            "loser": loser,
            "reported_by": ctx.author.name
        }

        # Write the match result to a CSV file
        file_exists = os.path.isfile("match-results.csv")
        with open("match-results.csv", "a", newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=["team_name", "opponent_team_name", "team_score", "opponent_score", "winner", "loser", "reported_by"])
            if not file_exists:
                writer.writeheader()  # Write header only if the file doesn't exist
            writer.writerow(match_result)  # Write the match result

        await ctx.send(f"Match result reported successfully! The winner is {winner}!")

    except ValueError:
        await ctx.send("Invalid input. Please ensure scores are integers and all arguments are provided correctly.")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)