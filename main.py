import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from pymongo import MongoClient

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
mongo_uri = os.getenv('MONGO_URI')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# MongoDB setup
client = MongoClient(mongo_uri)
db = client['pdl_bot']
matches = db['matches']
teams = db['teams']

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

@bot.command()
@commands.has_permissions(administrator=True)
async def add_team(ctx, *, args: str):
    """Add a team to the database. Usage: !add_team Team Name"""
    parts = [part.strip() for part in args.split(',', 1)]
    if len(parts) != 2:
        await ctx.send("Please provide the team name and discord_user, separated by a comma. Example: !add_team Team Name, Discord Username")
        return
    team_name, discord_user = parts
    
    if not team_name or not discord_user:
        await ctx.send("Team name and Discord name cannot be empty.")
        return
    
    budget = 180  # Initial points to spend on roster (can be adjusted based on draft rules)

    existing_team = teams.find_one({"team_name": {"$regex": f"^{team_name}$", "$options": "i"}})
    existing_user = teams.find_one({"discord_user": {"$regex": f"^{discord_user}$", "$options": "i"}})
    if existing_team:
        await ctx.send(f"Team '{team_name}' already exists.")
        return
    if existing_user:
        await ctx.send(f"Discord user '{discord_user}' is already associated with a team.")
        return

    team_entry = {
        "team_name": team_name,
        "discord_user": discord_user,
        "budget": budget, 
        "roster": []
    }
    teams.insert_one(team_entry)
    await ctx.send(f"{discord_user} has added '{team_name}' to the league successfully!")

@bot.command()
@commands.has_permissions(administrator=True)
async def add_pokemon(ctx, *, args: str):
    """Add a Pokémon to a team's roster. Usage: !add_pokemon Team Name, Pokemon Name"""
    try:
        # Split arguments by comma, allowing for spaces in team names
        parts = [part.strip() for part in args.split(',', 1)]
        if len(parts) != 2:
            await ctx.send("Please provide the team name and Pokémon name, separated by a comma. Example: !add_pokemon Team Name, Pikachu")
            return
        team_name, pokemon_name = parts
        
        if not team_name or not pokemon_name:
            await ctx.send("Team name, and Pokémon name cannot be empty.")
            return
        roster_entry = {
            "team_name": team_name,
            "pokemon_name": pokemon_name
        }
        try:
            teams.update_one(
                {"team_name": {"$regex": f"^{team_name}$", "$options": "i"}},
                {"$push": {"roster": roster_entry}}
            )
        except Exception:
            await ctx.send("An error occurred while adding the Pokémon to the roster.")
            return
        await ctx.send(f"Added {pokemon_name} to {team_name}'s roster!")
    except Exception as e:
        await ctx.send("An error occurred while adding the Pokémon.")

@bot.command()
async def report_match(ctx, *, args: str):
    try:
        # Split arguments by comma and strip whitespace
        parts = [part.strip() for part in args.split(', ')]
        if len(parts) != 4:
            await ctx.send("Please provide 4 arguments separated by commas: team_name, opponent_team_name, team_score, opponent_score")
            return
        
        team_name, opponent_team_name, team_score_str, opponent_score_str = parts
        
        # Convert scores to integers
        try:
            team_score = int(team_score_str)
            opponent_score = int(opponent_score_str)
        except ValueError:
            await ctx.send("Scores must be integers.")
            return
        
        if team_score < 0 or opponent_score < 0:
            await ctx.send("Scores must be non-negative integers.")
            return
        if not team_name.strip() or not opponent_team_name.strip():
            await ctx.send("Team names cannot be empty.")
            return
        if team_name == opponent_team_name:
            await ctx.send("You cannot report a match against the same team.")
            return
        if team_score == opponent_score:
            await ctx.send("Match cannot be reported as a draw.")
            return
        
        if not teams.find_one({"team_name": {"$regex": f"^{team_name}$", "$options": "i"}}):
            await ctx.send(f"Team '{team_name}' does not exist in this league. Please check for any typos and if the problem still persists, contact league administrator.")
            return
        if not teams.find_one({"team_name": {"$regex": f"^{opponent_team_name}$", "$options": "i"}}):
            await ctx.send(f"Team '{opponent_team_name}' does not exist in this league. Please check for any typos and if the problem still persists, contact league administrator.")
            return

        winner = team_name if team_score > opponent_score else opponent_team_name
        loser = opponent_team_name if team_score > opponent_score else team_name

        match_result = {
            "team_name": team_name,
            "opponent_team_name": opponent_team_name,
            "team_score": team_score,
            "opponent_score": opponent_score,
            "winner": winner,
            "loser": loser,
            "reported_by": ctx.author.name
        }

        matches.insert_one(match_result)
        await ctx.send(f"Match result reported successfully!")

    except Exception:
        await ctx.send("Invalid input. Please ensure you use: !report_match team_name, opponent_team_name, team_score, opponent_score")

@bot.command()
async def view_matches(ctx):
    results = list(matches.find())
    if not results:
        await ctx.send("No match results found. Please use !report_match to report a match.")
        return
    for row in results:
        await ctx.send(
            f"{row['team_name']} vs {row['opponent_team_name']} | "
            f"Score: {row['team_score']} - {row['opponent_score']} | "
            f"Winner: {row['winner']}"
        )

@bot.command()
async def show_standings(ctx):
    results = list(matches.find())
    if not results:
        await ctx.send("No match results found.")
        return

    standings = {}
    for row in results:
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

    sorted_standings = sorted(standings.items(), key=lambda x: x[1]['points'], reverse=True)

    # Build Markdown table
    table = ["**Standings:**",
             "```markdown",
             "| Team                | Wins | Losses | Points |",
             "|---------------------|------|--------|--------|"]
    for team, stats in sorted_standings:
        table.append(f"| {team:<19} | {stats['wins']:^4} | {stats['losses']:^6} | {stats['points']:^6} |")
    table.append("```")
    await ctx.send("\n".join(table))

@bot.command()
async def show_roster(ctx, *, team_name: str):
    """Show the roster for a team. Usage: !show_roster Team Name"""
    team = teams.find_one({"team_name": {"$regex": f"^{team_name}$", "$options": "i"}})
    if not team:
        await ctx.send(f"No roster found for team: {team_name}")
        return
    roster = team.get("roster", [])
    if not roster:
        await ctx.send(f"No Pokémon found in {team_name}'s roster.")
        return

    # Build a Markdown-formatted roster
    roster_lines = [f"**Roster for _{team['team_name']}_:**\n"]
    for idx, entry in enumerate(roster, 1):
        roster_lines.append(f"`{idx}.` **{entry['pokemon_name']}**")
    roster_message = "\n".join(roster_lines)

    await ctx.send(roster_message)

@bot.command()
@commands.has_permissions(administrator=True)
async def clear_all(ctx):
    """Clear all matches, rosters, and teams from the database."""
    matches.delete_many({})
    teams.delete_many({})
    await ctx.send("All matches, rosters, and teams have been cleared from the database.")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)