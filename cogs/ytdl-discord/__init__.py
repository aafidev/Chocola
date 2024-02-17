import nextcord
from nextcord.ext import commands
from pytube import YouTube
from pydub import AudioSegment
import os
import time

# The following lines should be at the end of your script
intents = nextcord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=">>", intents=intents)


class YTDL(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx, error):
        await ctx.send(f"An error occurred: {error}")

    @commands.command(
        name="ytdl", description="Download audio from YouTube and send as an MP3 file."
    )
    async def ytdl_command(self, ctx: commands.Context, query: str):
        # Ensure the "downloads" directory exists
        downloads_dir = "downloads"
        os.makedirs(downloads_dir, exist_ok=True)

        try:
            # Check if the input is a URL or a search query
            if "youtube.com" in query or "youtu.be" in query:
                # Direct URL provided
                video = YouTube(query)
            else:
                # Search query provided
                videos = YouTube().search(query)
                if not videos:
                    await ctx.send("No videos found for the provided search query.")
                    return

                # Present a list of search results to the user
                search_results = "\n".join(
                    [f"{i + 1}. {video.title}" for i, video in enumerate(videos)]
                )
                await ctx.send(
                    f"Search Results:\n{search_results}\n\nPlease choose a number from the list."
                )

                def check(message):
                    return (
                        message.author == ctx.author and message.channel == ctx.channel
                    )

                # Wait for user input to select a video
                response = await self.bot.wait_for("message", check=check, timeout=30)
                choice = int(response.content) - 1

                if not 0 <= choice < len(videos):
                    await ctx.send(
                        "Invalid choice. Please choose a number from the list."
                    )
                    return

                video = videos[choice]

            # Check if the audio stream is available
            stream = video.streams.filter(only_audio=True).first()
            if stream is None:
                await ctx.send(
                    "No audio stream available for the selected YouTube video."
                )
                return

            # Download the audio stream as MP4
            mp4_file_path = os.path.join(downloads_dir, f"{video.title}.mp4")
            stream.download(output_path=downloads_dir)

            # Convert MP4 to MP3 using pydub
            mp3_file_path = os.path.join(downloads_dir, f"{video.title}.mp3")
            audio = AudioSegment.from_file(mp4_file_path, format="mp4")
            audio.export(mp3_file_path, format="mp3")

            # Send the MP3 file to the text channel
            await ctx.send(file=nextcord.File(mp3_file_path))

            # Send an embed with information about the YouTube video
            embed = nextcord.Embed(
                title=video.title,
                url=video.watch_url,
                description=f"Uploaded by {video.author}\nDuration: {video.length} seconds",
                color=0x00FF00,  # You can customize the color as needed
            )
            embed.set_thumbnail(url=video.thumbnail_url)
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error: {e}")
            await ctx.send(f"An error occurred: {e}")

        finally:
            # Clean up the temporary files if they were created
            if "mp4_file_path" in locals() and os.path.exists(mp4_file_path):
                os.remove(mp4_file_path)
            if "mp3_file_path" in locals() and os.path.exists(mp3_file_path):
                os.remove(mp3_file_path)

        # Add a delay between requests
        time.sleep(1)  # Sleep for 1 second

    @ytdl_command.error
    async def ytdl_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please provide a valid YouTube URL or search query.")
            return

        await ctx.send(f"An error occurred: {error}")


def setup(bot):
    bot.add_cog(YTDL(bot))
    print("Loaded ytdl cog")
