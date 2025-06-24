import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import sys

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
mongo_uri = os.getenv('MONGO_URI')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# MongoDB setup
client = MongoClient(mongo_uri,server_api=ServerApi('1'))
db = client['pdl_bot']
matches = db['matches']
teams = db['teams']

try:
    client.admin.command('ping')
    print("You are connected to MongoDB!")
except Exception as e:
    print("Failed to connect to MongoDB:", e)
    sys.exit(1) #1 stops the bot from running if MongoDB is not connected

@bot.event
async def on_ready():
    print("Bot is ready!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def add_team(ctx, *, args: str):
    """Add a team to the database. Usage: !add_team Team Name"""
    parts = [part.strip() for part in args.split(',')]
    if len(parts) != 2:
        await ctx.send("Please provide the team name and discord_user, separated by a comma. Example: !add_team Team Name, Discord Username")
        return
    team_name, discord_user = parts
    
    if not team_name or not discord_user:
        await ctx.send("Team name and Discord name cannot be empty.")
        return
    
    budget = 180  # Initial points to spend on roster (can be adjusted based on draft rules)
    team_name = team_name.title()
    discord_user = discord_user.lower()

    if teams.find_one({
        "$or":[
               {"team:name": {"regex": f"^{team_name}$", "$options": "i"}},
               {"discord_user": {"$regex": f"^{discord_user}$", "$options": "i"}}]
    }):
        await ctx.send(f"Team '{team_name}' or user '{discord_user}' already exists in the league.")
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
    """Add a Pokémon to a team's roster. Usage: !add_pokemon Team Name, Pokemon Name, PointValue"""
    
    # Split arguments by comma, allowing for spaces in team names
    parts = [part.strip() for part in args.split(',', 2)]
    if len(parts) != 3:
        await ctx.send("Please provide the team name, Pokémon name, and point value, separated by a comma. Example: !add_pokemon Team Name, Pikachu, 20")
        return
    team_name, pokemon_name, pokemon_value = parts
    pokemon_name = pokemon_name.title()
    team_name = team_name.title()

    if not pokemon_value.isdigit() or int(pokemon_value) < 0:
        await ctx.send("Point value must be a positive number.")
        return
        
    if not team_name or not pokemon_name or not pokemon_value:
        await ctx.send("Team name, Pokémon name, and point value cannot be empty.")
        return
    roster_entry = {
        "pokemon_name": pokemon_name,
        "point_value": int(pokemon_value)
    }
    if team_name not in [team['team_name'] for team in teams.find()]:
        await ctx.send(f"Team '{team_name}' does not exist. Please create the team first using !add_team.")
        return
    teams.update_one(
        {"team_name": {"$regex": f"^{team_name}$", "$options": "i"}},
        {"$push": {"roster": roster_entry}})
    teams.update_one(
        {"team_name": {"$regex": f"^{team_name}$", "$options": "i"}},
        {"$inc": {"budget": -int(pokemon_value)}}
    )
    await ctx.send(f"Added {pokemon_name} to {team_name}'s roster!")

@bot.command()
@commands.has_permissions(administrator=True)
async def schedule_match(ctx, *, args:str):
    parts = [part.strip() for part in args.split(',')]
    if len(parts) != 5:
        await ctx.send("Please provide 5 arguments separated by commas: week number, team name, discord_user, opponent team name, opponent discord_user")
        return
    
    week, team_name, discord_user, opponent_team_name, opponent_discord_user = parts
    team_name = team_name.title()
    opponent_team_name = opponent_team_name.title()
    discord_user = discord_user.lower()
    opponent_discord_user = opponent_discord_user.lower()

    match_result = {
        "week": week,
        "team_name": team_name,
        "discord_user": discord_user,
        "opponent_team_name": opponent_team_name,
        "opponent_discord_user": opponent_discord_user,
        "team_score": 0,
        "opponent_score": 0,
        "winner": "N/A",
        "loser": "N/A",
        "reported_by": "N/A"
    }
    matches.insert_one(match_result)
    await ctx.send(f"Match added to schedule successfully!")


@bot.command()
async def show_matches(ctx, *, search_text: str):
    if search_text is None or search_text.strip() == "":
        await ctx.send("Please provide a search term (week number, team name, or opponent team name).")
        return
        
    searched_matches = matches.find({
    "$or": [
        {"week": {"$regex": f"^{search_text}$", "$options": "i"}},
        {"team_name": {"$regex": f"^{search_text}$", "$options": "i"}},
        {"opponent_team_name": {"$regex": f"^{search_text}$", "$options": "i"}},
        {"discord_user": {"$regex": f"^{search_text}$", "$options": "i"}},
        {"opponent_discord_user": {"$regex": f"^{search_text}$", "$options": "i"}}
        ]
    })
    searched_matches = list(searched_matches)
    searched_matches.sort(key=lambda x: (x['week'], x['team_name'], x['opponent_team_name']))
    
    if not searched_matches:
        await ctx.send(f"'{search_text}' not found. Please try again with a week number, team name, or opponent team name featured in the schedule.")
        return
    
    table = [
    "```markdown",
    "| Week | Team                | Opponent             | Score |",
    "|------|---------------------|----------------------|-------|"
]
    for match in searched_matches:
        if match['winner'] == "N/A":
            table.append(f"| {match['week']:<4} | {match['team_name']:<19} | {match['opponent_team_name']:<20} | N/A   |")
        elif match['winner'] == "DNP":
            table.append(f"| {match['week']:<4} | {match['team_name']:<19} | {match['opponent_team_name']:<20} | DNP   |")
        else:
            table.append(f"| {match['week']:<4} | {match['team_name']:<19} | {match['opponent_team_name']:<20} | {match['team_score']} - {match['opponent_score']} |")
    table.append("```")
    await ctx.send("\n".join(table))
        
@bot.command()
async def report_match(ctx, *, args: str):
    # Split arguments by comma and strip whitespace
    parts = [part.strip() for part in args.split(',')]
    if len(parts) != 4:
        await ctx.send("Please provide 4 arguments separated by commas: team_name, opponent_team_name, team_score, opponent_score")
        return
    
    team_name, opponent_team_name, team_score_str, opponent_score_str = parts
    # Convert scores to integers    
    team_score = int(team_score_str)
    opponent_score = int(opponent_score_str) 
    
    if team_score < 0 or opponent_score < 0:
        await ctx.send("Scores must be non-negative integers.")
        return
    if not team_name.strip() or not opponent_team_name.strip():
        await ctx.send("Team names cannot be empty.")
        return
    if team_name == opponent_team_name:
        await ctx.send("You cannot report a match against the same team.")
        return

    if team_score > opponent_score:
        winner = team_name
        loser = opponent_team_name
    elif team_score < opponent_score:
        winner = opponent_team_name
        loser = team_name
    else:
        winner = "DNP"
        loser = "DNP"
    
    if not teams.find_one({
        "$or": [
            {"team_name": {"$regex": f"^{team_name}$", "$options": "i"}},
            {"discord_user": {"$regex": f"^{team_name}$", "$options": "i"}}
        ]
        }):
        await ctx.send(f"Team or user '{team_name}' not found. Please check the spelling and try again.")
        return

    # Check if opponent exists
    if not teams.find_one({
            "$or": [
                {"team_name": {"$regex": f"^{opponent_team_name}$", "$options": "i"}},
                {"discord_user": {"$regex": f"^{opponent_team_name}$", "$options": "i"}}
            ]
        }):
        await ctx.send(f"Team or user '{opponent_team_name}' not found. Please check the spelling and try again.")
        return
    
    match = matches.update_one({
        "$or": [
            {
                "$and": [
                    {
                        "$or": [
                            {"team_name": {"$regex": f"^{team_name}$", "$options": "i"}},
                            {"discord_user": {"$regex": f"^{team_name}$", "$options": "i"}}
                        ]
                    },
                    {
                        "$or": [
                            {"opponent_team_name": {"$regex": f"^{opponent_team_name}$", "$options": "i"}},
                            {"opponent_discord_user": {"$regex": f"^{opponent_team_name}$", "$options": "i"}}
                        ]
                    },
                    {"winner": "N/A"}
                ]
            },
            {
                "$and": [
                    {
                        "$or": [
                            {"team_name": {"$regex": f"^{opponent_team_name}$", "$options": "i"}},
                            {"discord_user": {"$regex": f"^{opponent_team_name}$", "$options": "i"}}
                        ]
                    },
                    {
                        "$or": [
                            {"opponent_team_name": {"$regex": f"^{team_name}$", "$options": "i"}},
                            {"opponent_discord_user": {"$regex": f"^{team_name}$", "$options": "i"}}
                        ]
                    },
                    {"winner": "N/A"}
                ]
            }
        ]
    },
    {
        "$set": {
            "team_score": team_score,
            "opponent_score": opponent_score,
            "winner": winner,
            "loser": loser,
            "reported_by": ctx.author.name
        }
    })
    
    if match.modified_count == 0:
        await ctx.send("Match not in schedule or is already reported. Please ensure the match is scheduled and has not been reported yet.") 
        return
    await ctx.send(f"Match result reported successfully!")

@bot.command()
async def show_teams(ctx):
    results = list(teams.find())
    if not results:
        await ctx.send("No teams found in the league.")
        return
    table = ["```markdown",
            "| Team                | Discord User        | Budget |",
            "|---------------------|---------------------|--------|"]
    for team in results:
        team_name = team['team_name']
        if len(team['team_name']) > 19:
            short_team_name = team_name[:16] + "..." 
            table.append(f"| {short_team_name:<19} | {team['discord_user']:<19} | {team['budget']:>6} |")
        else:
            table.append(f"| {team_name:<19} | {team['discord_user']:<19} | {team['budget']:>6} |")
    table.append("```")
    await ctx.send("\n".join(table))

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
            standings[team] = {'wins': 0, 'losses': 0, 'DNP': 0, 'points': 0}
        if opponent not in standings:
            standings[opponent] = {'wins': 0, 'losses': 0, 'DNP': 0, 'points': 0}

        winner_points = 3
        loser_points = 1
            
        if winner == team:
            standings[team]['wins'] += 1
            standings[team]['points'] += winner_points
            standings[opponent]['losses'] += 1
            standings[opponent]['points'] += loser_points
        elif winner == opponent:
            standings[opponent]['wins'] += 1
            standings[opponent]['points'] += winner_points
            standings[team]['losses'] += 1
            standings[team]['points'] += loser_points
        elif winner == "DNP":
            standings[team]['DNP'] += 1
            standings[opponent]['DNP'] += 1
        else:
            pass

    sorted_standings = sorted(standings.items(), key=lambda x: x[1]['points'], reverse=True)

    # Build Markdown table
    table = ["```markdown",
            "| Team                | Wins | Losses | DNP | Points |",
            "|---------------------|------|--------|-----|--------|"]
    for team, stats in sorted_standings:
        table.append(f"| {team:<19} | {stats['wins']:^4} | {stats['losses']:^6} | {stats['DNP']:^3} | {stats['points']:^6} |")
    table.append("```")
    await ctx.send("\n".join(table))

@bot.command()
async def show_roster(ctx, *, team_name: str):
    """Show the roster for a team. Usage: !show_roster Team Name"""
    team = teams.find_one({
    "$or": [
        {"team_name": {"$regex": f"^{team_name}$", "$options": "i"}},
        {"discord_user": {"$regex": f"^{team_name}$", "$options": "i"}}
    ]
})
    if not team:
        await ctx.send(f"There is no team or player titled: {team_name} in this league.")
        return
    roster = team.get("roster", [])
    if not roster:
        await ctx.send(f"No Pokémon found in {team_name}'s roster.")
        return

    # Build a Markdown-formatted roster
    roster_lines = [f"** {team['team_name']}'s Roster** (User: {team['discord_user']})"]
    for idx, entry in enumerate(roster, 1):
        roster_lines.append(f"`{idx}.` {entry['pokemon_name']} (*Pts: {entry['point_value']}*)")
    roster_lines.append(f"Budget Remaining: *{team['budget']} points*")
    roster_message = "\n".join(roster_lines)
    await ctx.send(roster_message)

@bot.command()
async def check(ctx, *, team_name: str):
    """Check if a user is registered in the league. Usage: !check_user Team Name"""
    team = teams.find_one({
        "$or": [
            {"team_name": {"$regex": f"^{team_name.title()}$", "$options": "i"}},
            {"discord_user": {"$regex": f"^{team_name.lower()}$", "$options": "i"}}
        ]
    })
    if not team:
        await ctx.send(f"There is no team titled: {team_name} in this league.")
        return
    await ctx.send(f"{team['team_name']} is {team['discord_user']}'s team in the league.")

@bot.command()
@commands.has_permissions(administrator=True)
async def clear_all(ctx):
    """Clear all matches, rosters, and teams from the database."""
    matches.delete_many({})
    teams.delete_many({})
    await ctx.send("All matches, rosters, and teams have been cleared from the database.")

@bot.command()
@commands.has_permissions(administrator=True)
async def clear_roster(ctx, team_name: str):
    """Clear the roster for a specific team."""
    result = teams.update_one(
        {"team_name": {"$regex": f"^{team_name}$", "$options": "i"}},
        {"$set": {"roster": [], "budget": 180}}  # Reset budget to initial value
    )
    if result.modified_count > 0:
        await ctx.send(f"{team_name}'s roster has been cleared.")
    else:
        await ctx.send(f"No team found with the name '{team_name}'.")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)