import nextcord
from nextcord.ext import commands
import sqlite3
import random
import os
import json

class Someone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "cogs/someone/someonedb/members.db"
        self.guild_id_path = "cogs/someone/someonedb/guild_id.json"
        self.setup_database()

    def setup_database(self):
        # Create the directory if it doesn't exist
        directory = os.path.dirname(self.db_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Connect to the database or create it if it doesn't exist
        self.db_connection = sqlite3.connect(self.db_path)
        cursor = self.db_connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY,
                member_id INTEGER UNIQUE
            )
        ''')
        self.db_connection.commit()

    def get_all_member_ids(self):
        return [member.id for member in self.bot.get_all_members()]

    def get_guild_id(self):
        return self.bot.guilds[0].id if self.bot.guilds else None

    def save_guild_id(self):
        guild_id = self.get_guild_id()
        if guild_id:
            with open(self.guild_id_path, "w") as file:
                json.dump({"guild_id": guild_id}, file)

    def load_guild_id(self):
        try:
            with open(self.guild_id_path, "r") as file:
                data = json.load(file)
                return data.get("guild_id")
        except FileNotFoundError:
            return None

    def scan_all_members(self):
        member_ids = [member.id for member in self.bot.get_all_members()]
        cursor = self.db_connection.cursor()

        for member_id in member_ids:
            cursor.execute('''
                INSERT OR IGNORE INTO members (member_id) VALUES (?)
            ''', (member_id,))

        self.db_connection.commit()
        return member_ids

    @nextcord.slash_command(name="scan_members")
    async def scan_members(self, ctx):
        member_ids = self.scan_all_members()
        await ctx.send(f"Scanned and added {len(member_ids)} members to the database.")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        await self.bot.guilds[0].fetch_members(limit=None).flatten()
        self.scan_all_members()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        cursor = self.db_connection.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO members (member_id) VALUES (?)
        ''', (member.id,))
        self.db_connection.commit()

    @nextcord.slash_command(name="someone")
    async def _someone(self, ctx):
        member_ids = self.scan_all_members()

        if not member_ids:
            await ctx.send("No members found in the server.")
            return

        member_id = random.choice(member_ids)
        try:
            user = await ctx.guild.fetch_member(member_id)
        except nextcord.NotFound:
            await ctx.send("Couldn't find the selected member.")
            return

        await ctx.send(f"{user.mention}")


def setup(bot):
    cog = Someone(bot)
    bot.add_cog(cog)
    cog.save_guild_id()
    print("Someone loaded")
