import nextcord
from nextcord.ext import commands
import aiosqlite
import os
from datetime import datetime
import re

class QuotesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.moyai_emoji = '\U0001F5FF'  # Moyai emoji
        self.create_channel_threshold = 1  # Change this threshold as needed

    async def create_tables(self):
        # Create the 'db' directory if it doesn't exist
        os.makedirs('cogs/quotes/db/', exist_ok=True)

        # Connect to the SQLite database using aiosqlite
        self.bot.db = await aiosqlite.connect('cogs/quotes/db/quotes.db')

        # Create the 'quotes' table in the database if it doesn't exist
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                author TEXT,
                timestamp TEXT,
                is_text_embed INTEGER
            )
        ''')
        await self.bot.db.commit()

        # Create the 'channels' table in the database if it doesn't exist
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                guild_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY (guild_id, channel_id)
            )
        ''')
        await self.bot.db.commit()

        # Create the 'reactions' table in the database if it doesn't exist
        await self.bot.db.execute('''
            CREATE TABLE IF NOT EXISTS reactions (
                channel_id INTEGER,
                message_id INTEGER,
                PRIMARY KEY (channel_id, message_id)
            )
        ''')
        await self.bot.db.commit()

    async def is_text_embed(self, message):
        # Check if the message has a Tenor link or any link that displays an image
        if any(re.search(r'(https?://\S+tenor.com/\S+)', message.content) for message in message.attachments):
            return False

        # Check if the message has attachments (images or GIFs)
        if message.attachments and any(attachment.content_type.startswith('image') for attachment in message.attachments):
            return False

        if message.embeds and any(embed.type == 'image' for embed in message.embeds):
            return False

        return True

    async def process_quote_reaction(self, message, moyai_reaction):
        # Your existing code to process the quote reaction
        quote_content = message.content
        quote_author = message.author.display_name
        is_text_embed = await self.is_text_embed(message)

        # Save the quote to the database
        await self.bot.db.execute(
            'INSERT INTO quotes (content, author, timestamp, is_text_embed) VALUES (?, ?, ?, ?)',
            (quote_content, quote_author, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), is_text_embed))

        # Commit the changes to the database
        await self.bot.db.commit()

        # Send the quote to the appropriate channel
        quotes_channel = nextcord.utils.get(message.guild.channels, name='quotes')
        if quotes_channel:
            if is_text_embed:
                # Create an embed for the quote
                embed = nextcord.Embed(title=f"Quote by {quote_author}", description=quote_content,
                                       color=nextcord.Color.blue())
                embed.set_footer(text=f"Quoted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
                await quotes_channel.send(embed=embed)
            else:
                # Send the message content as a regular message
                await quotes_channel.send(f'{quote_content}\n - {quote_author}')

        # Log the quote to a file
        await self.log_quote(quote_content, quote_author, datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'))

        # Print a message indicating that the quote was saved
        print(f'Quote saved: "{quote_content}" - {quote_author}')

    async def log_quote(self, content, author, timestamp):
        # Create the 'logs' directory if it doesn't exist
        os.makedirs('cogs/quotes/logs/', exist_ok=True)

        # Write the quote to the log file
        log_file_path = f'cogs/quotes/logs/quotes_log.txt'
        with open(log_file_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f'[{timestamp}] {author}: {content}\n')

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Logged in as {self.bot.user.name}')
        # Create tables if they don't exist
        await self.create_tables()

        # Iterate through the channels in the database and check for reactions
        async with self.bot.db.execute('SELECT guild_id, channel_id FROM channels') as cursor:
            async for row in cursor:
                guild_id, channel_id = row
                guild = self.bot.get_guild(guild_id)
                if guild:
                    channel = guild.get_channel(channel_id)
                    if channel:
                        # Fetch messages from the database for the given channel
                        async with self.bot.db.execute('SELECT message_id FROM reactions WHERE channel_id = ?', (channel_id,)) as msg_cursor:
                            messages_in_db = {row[0] for row in await msg_cursor.fetchall()}

                            # Read message history in the channel and process reactions
                            async for old_message in channel.history(limit=None, oldest_first=True):
                                if old_message.id not in messages_in_db:
                                    moyai_reaction = next(
                                        (react for react in old_message.reactions if str(react.emoji) == self.moyai_emoji), None)
                                    if moyai_reaction and moyai_reaction.count >= self.create_channel_threshold:
                                        # Process the reaction as before
                                        await self.process_quote_reaction(old_message, moyai_reaction)

                                        # Update the 'reactions' table in the database
                                        await self.bot.db.execute('INSERT OR IGNORE INTO reactions (channel_id, message_id) VALUES (?, ?)',
                                                                  (channel.id, old_message.id))
                                        await self.bot.db.commit()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if reaction.emoji == self.moyai_emoji:
            print(f'Reaction added: {reaction.emoji} by {user.name} in {reaction.message.channel.name}')
            print(f'Message content: {reaction.message.content}')

            # Find the moyai reaction object
            moyai_reaction = next(
                (react for react in reaction.message.reactions if str(react.emoji) == self.moyai_emoji), None)

            if moyai_reaction and moyai_reaction.count >= self.create_channel_threshold:
                # Process the reaction as before
                await self.process_quote_reaction(reaction.message, moyai_reaction)

                # Update the 'reactions' table in the database
                await self.bot.db.execute('INSERT OR IGNORE INTO reactions (channel_id, message_id) VALUES (?, ?)',
                                          (reaction.message.channel.id, reaction.message.id))
                await self.bot.db.commit()

            # Check if the "quotes" channel exists, and create it if the threshold is reached
            quotes_channel = nextcord.utils.get(reaction.message.guild.channels, name='quotes')
            if not quotes_channel and moyai_reaction and moyai_reaction.count >= self.create_channel_threshold:
                quotes_channel = await reaction.message.guild.create_text_channel(name='quotes')

                # Add the channel to the database
                await self.bot.db.execute('INSERT OR IGNORE INTO channels (guild_id, channel_id) VALUES (?, ?)',
                                          (reaction.message.guild.id, quotes_channel.id))
                # Print a message indicating that the channel was created
                print(f"Created channel {quotes_channel.name} in {reaction.message.guild.name}")

                # Once the "quotes" channel is created, send an embed to the channel
                embed = nextcord.Embed(title="Welcome to the Quotes Channel!",
                                       description="This channel is dedicated to sharing quotes.",
                                       color=nextcord.Color.blue())
                await quotes_channel.send(embed=embed)

    @commands.command(name='setthreshold', aliases=['st'])
    async def set_threshold(self, ctx, threshold: int):
        """
        Set the threshold for creating the "quotes" channel.
        Example: !setthreshold 5
        """
        self.create_channel_threshold = max(threshold, 1)
        await ctx.send(f'Threshold set to {self.create_channel_threshold} reactions for creating the "quotes" channel.')

    @commands.command(name='quotescanall')
    async def quotes_scan_all(self, ctx):
        """
        Scan all messages in all channels and save quotes to the log.
        """
        await ctx.send('Scanning all messages for quotes...')
        for guild in self.bot.guilds:
            for channel in guild.channels:
                if isinstance(channel, nextcord.TextChannel):
                    async for message in channel.history(limit=None):
                        if self.moyai_emoji in [str(react.emoji) for react in message.reactions]:
                            # Process the message as a quote
                            moyai_reaction = next(
                                (react for react in message.reactions if str(react.emoji) == self.moyai_emoji), None)
                            if moyai_reaction and moyai_reaction.count >= self.create_channel_threshold:
                                await self.process_quote_reaction(message, moyai_reaction)

        await ctx.send('Quotes scan completed.')

    def cog_unload(self):
        # Close the database connection
        self.bot.loop.create_task(self.bot.db.close())

def setup(bot):
    bot.add_cog(QuotesCog(bot))
    print("Quotes loaded")
