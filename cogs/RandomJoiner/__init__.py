import nextcord
from nextcord.ext import commands, tasks
import asyncio
import random
import json
import os
from pytube import YouTube
import sqlite3


class SoundCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.enabled_servers = (
            self.load_enabled_servers()
        )  # Load enabled servers from file
        self.voice_clients = {}  # Store voice clients per guild
        self.played_sounds = {}  # Dictionary to store played sounds per guild
        self.check_vc.start()

        # Database setup
        self.db_path = os.path.join("cogs", "RandomJoiner", "custom_sounds.db")
        self.create_db()

    def cog_unload(self):
        self.check_vc.cancel()

    def load_enabled_servers(self):
        file_path = os.path.join("cogs", "RandomJoiner", "enabled_servers.json")
        try:
            with open(file_path, "r") as file:
                content = file.read()
                if not content:
                    return set()
                return set(json.loads(content))
        except FileNotFoundError:
            return set()
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return set()

    def save_enabled_servers(self):
        file_path = os.path.join("cogs", "RandomJoiner", "enabled_servers.json")
        try:
            with open(file_path, "w") as file:
                json.dump(list(self.enabled_servers), file)
        except FileNotFoundError:
            os.makedirs(os.path.join("cogs", "RandomJoiner"), exist_ok=True)
            with open(file_path, "w") as file:
                json.dump(list(self.enabled_servers), file)

    def create_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create a table for custom sounds
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS custom_sounds (
                guild_id INTEGER,
                sound_name TEXT,
                sound_url TEXT
            )
        """
        )

        conn.commit()
        conn.close()

    def get_custom_sounds(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Retrieve all custom sounds from the database
        cursor.execute("SELECT guild_id, sound_url FROM custom_sounds")
        results = cursor.fetchall()

        conn.close()

        # Organize the results by guild_id
        custom_sounds_dict = {}
        for result in results:
            guild_id, sound_url = result
            if guild_id not in custom_sounds_dict:
                custom_sounds_dict[guild_id] = []
            custom_sounds_dict[guild_id].append(sound_url)

        return custom_sounds_dict

    @tasks.loop(seconds=5)
    async def check_vc(self):
        for guild in self.bot.guilds:
            if guild.id in self.enabled_servers:
                for channel in guild.voice_channels:
                    if channel.members:
                        print(f"Checking voice channel {channel.name} in {guild.name}")
                        if (
                            guild.id not in self.voice_clients
                            or not self.voice_clients[guild.id].is_connected()
                        ):
                            # Connect to voice channel only if not already connected or disconnected
                            print(
                                f"Connecting to voice channel {channel.name} in {guild.name}"
                            )
                            try:
                                voice_client = await channel.connect()
                                self.voice_clients[guild.id] = voice_client
                            except Exception as e:
                                print(f"Error connecting to voice channel: {e}")
                                continue  # Continue to the next voice channel on error

                        # Play random sound only if not already playing
                        voice_client = self.voice_clients[guild.id]
                        if not voice_client.is_playing():
                            print(f"Playing random sound in {guild.name}")
                            try:
                                await self.play_random_sound(voice_client, guild.id)
                            except Exception as e:
                                print(f"Error playing random sound: {e}")

    async def play_random_sound(self, voice_client, guild_id):
        # Check for custom sounds in the database
        custom_sounds_dict = self.get_custom_sounds()

        if custom_sounds_dict:
            # Select a random custom sound file from all guilds
            all_custom_sounds = [
                sound
                for guild_sounds in custom_sounds_dict.values()
                for sound in guild_sounds
            ]
            custom_sound = random.choice(all_custom_sounds)
            sound_file = custom_sound
        else:
            # Use predefined sound effects if no custom sound is found
            sound_directory = "cogs/RandomJoiner/Sussy_FX"
            sound_files = [
                file for file in os.listdir(sound_directory) if file.endswith(".mp3")
            ]

            if not sound_files:
                print(f"No .mp3 files found in {sound_directory}")
                return

            # Find a new sound that hasn't been played yet
            available_sounds = set(sound_files) - self.played_sounds.get(
                guild_id, set()
            )

            if not available_sounds:
                print(f"All sounds have been played. Resetting the played sounds list.")
                self.played_sounds[guild_id] = set()
                available_sounds = set(sound_files)

            # Select a random sound file
            sound_file = os.path.join(
                sound_directory, random.choice(list(available_sounds))
            )

            # Add the selected sound to the list of played sounds
            self.played_sounds[guild_id].add(os.path.basename(sound_file))

        # Debugging: print the file path before playing
        print(f"Playing sound from file: {sound_file}")

        try:
            # Play the sound
            audio_source = nextcord.FFmpegPCMAudio(
                executable="ffmpeg", source=sound_file
            )
            event = asyncio.Event()

            def after_play(error):
                if error:
                    print(f"Error playing sound: {error}")
                event.set()

            voice_client.play(audio_source, after=after_play)

            # Wait for the sound to start playing
            while not voice_client.is_playing():
                await asyncio.sleep(1)
                print("Waiting for sound to start playing...")

            # Wait for the sound to finish playing
            while voice_client.is_playing():
                await asyncio.sleep(1)
                print("Still playing...")

            print("Sound playback finished.")

        except Exception as e:
            print(f"Error playing sound: {e}")
            # Handle the error as needed (e.g., log, notify, etc.)

        # Disconnect after the countdown
        await asyncio.sleep(2)  # Wait for a short delay before disconnecting
        await voice_client.disconnect()
        del self.voice_clients[guild_id]

        # Add live countdown before rejoining with a different sound effect
        countdown_duration = random.randint(10, 300)
        print(f"Live countdown for {countdown_duration} seconds before rejoining...")

        # Send live countdown messages
        for i in range(countdown_duration, 0, -1):
            print(f"\rRejoining in {i} seconds...", end="", flush=True)
            await asyncio.sleep(1)

        print("\rRejoining...")

        # Reconnect to the voice channel after the countdown
        try:
            channel = voice_client.channel
            voice_client = await channel.connect()
            self.voice_clients[guild_id] = voice_client
        except Exception as e:
            print(f"Error reconnecting to voice channel: {e}")

        # Debugging: Print information after rejoining
        guild = voice_client.guild
        print(f"Rejoined voice channel {channel.name} in {guild.name}")
        print(f"Is connected: {voice_client.is_connected()}")
        print(f"Is playing: {voice_client.is_playing()}")

    def get_custom_sound(self, guild_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Retrieve a custom sound for the given guild from the database
        cursor.execute(
            "SELECT sound_url FROM custom_sounds WHERE guild_id = ?", (guild_id,)
        )
        result = cursor.fetchone()

        conn.close()

        if result:
            return result[0]  # Return the URL of the custom sound
        else:
            return None  # Return None if no custom sound is found

    def save_custom_sound(self, guild_id, sound_name, sound_url):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Save the custom sound to the database
        cursor.execute(
            "INSERT INTO custom_sounds (guild_id, sound_name, sound_url) VALUES (?, ?, ?)",
            (guild_id, sound_name, sound_url),
        )

        conn.commit()
        conn.close()

    @commands.command(name="dls", description="Downloads the sound fx to the database.")
    async def download_sound_command(self, ctx, sound_url, sound_name):
        guild_id = ctx.guild.id

        """
        Downloads sound effects to the database.
        Usage : >>dls <yt_link> <name_of_the_sound>

        """
        # Download the sound from YouTube
        youtube_video = YouTube(sound_url)
        audio_stream = youtube_video.streams.filter(only_audio=True).first()

        # Ensure that the file extension is 'mp3'
        if not sound_name.lower().endswith(".mp3"):
            sound_name += ".mp3"

        # Save the audio file with the provided name and correct file extension
        audio_stream.download(
            output_path=os.path.join("cogs", "RandomJoiner", "Sussy_FX"),
            filename=sound_name,
        )

        # Construct the full path to the saved audio file
        sound_file = os.path.join("cogs", "RandomJoiner", "Sussy_FX", sound_name)

        # Save the custom sound to the database
        self.save_custom_sound(
            guild_id, sound_name[:-4], sound_file
        )  # Removing '.mp3' extension for the database

        embed = nextcord.Embed(
            title="Custom Sound Added",
            description=f'Custom sound "{sound_name[:-4]}" added successfully.',
            color=nextcord.Color.green(),
        )
        embed.set_thumbnail(url=youtube_video.thumbnail_url)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="es", description="Enables Sound FX!")
    async def enable_sound_command(self, ctx):
        """
        Enables random sound effects throughout the entire server. Usage: >>enable_sound or >>es

        """
        if ctx.guild.id not in self.enabled_servers:
            self.enabled_servers.add(ctx.guild.id)
            self.save_enabled_servers()  # Save enabled servers to file
            embed = nextcord.Embed(
                title="Sound effects enabled", color=nextcord.Color.green()
            )  # Create an embed
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.avatar.url
            )  # Set the author
            await ctx.send(embed=embed)
        else:
            embed = nextcord.Embed(
                title="Sound effects already enabled", color=nextcord.Color.red()
            )
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.avatar.url
            )  # Set the author
            await ctx.send(embed=embed)

    @commands.command(name="ds", description="Disables Sound FX!")
    async def disable_sound_command(self, ctx):
        """
        Disables random sound effects throughout the entire server. Usage: >>disable_sound or >>ds

        """
        if ctx.guild.id in self.enabled_servers:
            self.enabled_servers.remove(ctx.guild.id)
            self.save_enabled_servers()  # Save enabled servers to file
            embed = nextcord.Embed(
                title="Sound effects disabled for this server",
                color=nextcord.Color.red(),
            )
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.avatar.url
            )  # Set the author
            await ctx.send(embed=embed)
        else:
            embed = nextcord.Embed(
                title="Sound effects are already disabled", color=nextcord.Color.red()
            )
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.avatar.url
            )  # Set the author
            await ctx.send(embed=embed)

    @commands.command(name="dc", description="Disconnects from the VC!")
    async def disconnect(self, ctx):
        """
        Disconnects the bot from the voice channel: >>dc or >>disconnect
        """
        if ctx.guild.id in self.voice_clients:
            await self.voice_clients[ctx.guild.id].disconnect()
            del self.voice_clients[ctx.guild.id]
            embed = nextcord.Embed(
                title="Disconnected",
                description="Disconnected from voice channel.",
                color=nextcord.Color.green(),
            )
            await ctx.send(embed=embed)
        else:
            embed = nextcord.Embed(
                title="Error",
                description="Not connected to a voice channel.",
                color=nextcord.Color.red(),
            )
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(SoundCog(bot))
    print("Random Sound Cog Loaded")
