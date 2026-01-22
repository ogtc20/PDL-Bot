from discord.ext import commands
from db import teams, matches
import string

class Matches(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def show_matches(self, ctx, *, search_text: str):
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
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def schedule_match(self, ctx, *, args:str):
        parts = [part.strip() for part in args.split(',')]
        if len(parts) != 5:
            await ctx.send("Please provide 5 arguments separated by commas: week number, team name, discord_user, opponent team name, opponent discord_user")
            return
        
        week, team_name, discord_user, opponent_team_name, opponent_discord_user = parts
        team_name = string.capwords(team_name)
        opponent_team_name = string.capwords(opponent_team_name)
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


    @commands.command()
    async def show_matches(self, ctx, *, search_text: str):
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

    @commands.command()
    async def report_match(self, ctx, *, args: str):
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
    
    @commands.command()
    async def show_standings(self, ctx):
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

async def setup(bot):
    await bot.add_cog(Matches(bot))