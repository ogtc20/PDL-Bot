import discord
from discord.ext import commands
from db import teams
import string

class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def show_all_teams(self, ctx):
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
    

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_team(self, ctx, *, args: str):
        """Add a team to the database. Usage: !add_team Team_Name, Discord_User"""
        parts = [part.strip() for part in args.split(',')]
        if len(parts) != 2:
            await ctx.send("Please provide the Team_Name and Discord_User, separated by a comma; !add_team Team_Name, Discord_Username")
            return
        team_name, discord_user = parts
        
        if not team_name or not discord_user:
            await ctx.send("Team_Name and Discord_Name cannot be empty.")
            return
        
        total_team_budget = 100  # Initial points to spend on roster (can be adjusted based on draft rules)
        team_name = string.capwords(team_name)
        discord_user = discord_user.lower()

        if teams.find_one({
            "$or":[
                {"team:name": {"regex": f"^{team_name}$", "$options": "i"}},
                {"discord_user": {"$regex": f"^{discord_user}$", "$options": "i"}}]
        }):
            await ctx.send(f"Team '{team_name}' or User '{discord_user}' already exists in the league.")
            return

        team_entry = {
            "team_name": team_name,
            "discord_user": discord_user,
            "budget": total_team_budget, 
            "roster": [],
            "matches": []
        }
        teams.insert_one(team_entry)
        await ctx.send(f"{team_name} has been added to the league and will be managed by: \"{discord_user}\".")

    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def add_pokemon(self, ctx, *, args: str):
        """Add a Pokémon to a team's roster. Usage: !add_pokemon Team_Name, Pokemon_Name, Point_Value"""
        
        # Split arguments by comma, allowing for spaces in team names
        parts = [part.strip() for part in args.split(',', 2)]
        if len(parts) != 3:
            await ctx.send("Please provide the Team_Name, Pokemon_Name, and Point_Value, separated by a comma; !add_pokemon Team_Name, Pokemon_Name, Point_Value")
            return
        team_name, pokemon_name, pokemon_value = parts
        pokemon_name = string.capwords(pokemon_name)
        team_name = string.capwords(team_name)

        if not pokemon_value.isdigit() or int(pokemon_value) < 0:
            await ctx.send("Point_Value must be a positive number.")
            return
            
        if not team_name or not pokemon_name or not pokemon_value:
            await ctx.send("Team_Name, Pokemon_Name, and Point_Value cannot be empty.")
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

    @commands.command()
    async def show_roster(self, ctx, *, team_name: str):
        """Show the roster for a specific team. Usage: !show_roster Team Name"""
        team_name = string.capwords(team_name)
        team = teams.find_one({"team_name": {"$regex": f"^{team_name}$", "$options": "i"}})
        if not team:
            await ctx.send(f"No team found with the name '{team_name}'.")
            return
        roster = team.get('roster', [])
        if not roster:
            await ctx.send(f"{team_name} has no players in their roster.")
            return
        table = ["```markdown",
                "| Pokémon            | Point Value |",
                "|--------------------|-------------|"]
        for entry in roster:
            pokemon_name = entry['pokemon_name']
            point_value = entry['point_value']
            if len(pokemon_name) > 18:
                short_pokemon_name = pokemon_name[:15] + "..."
                table.append(f"| {short_pokemon_name:<18} | {point_value:>11} |")
            else:
                table.append(f"| {pokemon_name:<18} | {point_value:>11} |")
        table.append("```")
        await ctx.send("\n".join(table))

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def clear_roster(self, ctx, team_name: str):
        """Clear the roster for a specific team."""
        result = teams.update_one(
            {"team_name": {"$regex": f"^{team_name}$", "$options": "i"}},
            {"$set": {"roster": [], "budget": 180}}  # Reset budget to initial value
        )
        if result.modified_count > 0:
            await ctx.send(f"{team_name}'s roster has been cleared.")
        else:
            await ctx.send(f"No team found with the name '{team_name}'.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def delete_all_teams(self, ctx):
        teams.delete_many({})
        await ctx.send("All teams have been deleted.")

async def setup(bot):
    await bot.add_cog(Teams(bot))