import re
from nextcord.ext import commands
import asyncio

class TwitterFixCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # Check if the message is from a user and contains a Twitter link
        if message.author.bot:
            return  # Ignore messages from other bots

        tweet_url_match = re.search(
            r"https?://(?:www\.)?twitter\.com/([a-zA-Z0-9_]+)/status/(\d+)",
            message.content,
        )

        if tweet_url_match:
            tweet_url = tweet_url_match.group(0)
            fixed_url = tweet_url.replace('twitter.com', 'fxtwitter.com').replace('x.com', 'fxtwitter.com')

            # Send the fixed link
            sent_message = await message.channel.send(fixed_url)

            # Delete the original message after a delay (e.g., 5 seconds)
            await self.bot.loop.create_task(self.delete_after_delay(message, 5))

    async def delete_after_delay(self, original_message, delay_seconds):
        await asyncio.sleep(delay_seconds)
        try:
            await original_message.delete()
        except Exception as e:
            print(f"Error deleting original message: {e}")

def setup(bot):
    bot.add_cog(TwitterFixCog(bot))
    print("TwitterFixCog loaded")
