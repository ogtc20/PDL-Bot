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

        await ctx.send(f"Match result reported successfully!")

    except ValueError:
        await ctx.send("Invalid input. Please ensure scores are integers and all arguments are provided correctly.")

@bot.command()
async def view_matches(ctx):
    file_exists = os.path.isfile("match-results.csv")
    if not file_exists:
        await ctx.send("No match results found. Please use !report_match to report a match.")
        return

    with open('match-results.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        if not rows:
            await ctx.send("No match results found. Please use !report_match to report a match.")
            return
        for row in rows:
            await ctx.send(
                f"{row['team_name']} vs {row['opponent_team_name']} | "
                f"Score: {row['team_score']} - {row['opponent_score']} | "
                f"Winner: {row['winner']}"
            )

@bot.command()
async def view_standings(ctx):
    file_exists = os.path.isfile("match-results.csv")
    if not file_exists:
        await ctx.send("No match results found. Please use !report_match to report a match.")
        return
    
    standings = {}
    with open('match-results.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        for row in rows:
            team = row['team_name']
            opponent = row['opponent_team_name']
            winner = row['winner']

            if team not in standings:
                standings[team] = {'wins': 0, 'losses': 0, 'points': 0}
            if opponent not in standings:
                standings[opponent] = {'wins': 0, 'losses': 0, 'points': 0}
            
            winner_points = 3
            loser_points = 1
            
            if winner == team:
                standings[team]['wins'] += 1
                standings[team]['points'] += winner_points
                standings[opponent]['losses'] += 1
                standings[opponent]['points'] += loser_points

            else:
                standings[opponent]['wins'] += 1
                standings[opponent]['points'] += winner_points
                standings[team]['losses'] += 1
                standings[team]['points'] += loser_points
    
    # Sort the standings by points in descending order
    sorted_standings = sorted(standings.items(), key=lambda x: x[1]['points'], reverse=True)
    await ctx.send("Standings:\n")
    for team, stats in sorted_standings:
        await ctx.send(f"{team}: {stats['wins']} Wins, {stats['losses']} Losses, {stats['points']} Points\n")

@bot.command()
async def show_rosters(ctx):
    file_exists = os.path.isfile("rosters.csv")
    if not file_exists:
        await ctx.send("No rosters found.")
        return
    
    with open('rosters.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rosters = {}
        for row in reader:
            team_name = row['team_name']
            pokemon_name = row['pokemon_name']
            if team_name not in rosters:
                rosters[team_name] = []
            rosters[team_name].append(pokemon_name)
        
        response = "Rosters:\n"
        for team, pokemons in rosters.items():
            response += f"{team}: {', '.join(pokemons)}\n"
        await ctx.send(response)

@bot.command()
async def show_roster(ctx, team_name: str):
    file_exists = os.path.isfile("rosters.csv")
    if not file_exists:
        await ctx.send("No rosters found.")
        return
    
    with open('rosters.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        found = False
        for row in reader:
            if row['team_name'].lower() == team_name.lower():
                found = True
                await ctx.send(f"{row['pokemon_name']}")
        if not found:
            await ctx.send(f"No roster found for team: {team_name}")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)