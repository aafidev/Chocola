import os
import nextcord
from nextcord.ext import commands
import config

def main():
    intents = nextcord.Intents.default()
    intents.message_content = True  # Enable the message content intent
    intents.members = True  # Enable the members intent

    activity = nextcord.Activity(
        type=nextcord.ActivityType.listening, name=f"{config.BOT_PREFIX}help"
    )

    bot = commands.Bot(
        commands.when_mentioned_or(config.BOT_PREFIX),
        intents=intents,
        activity=activity,
    )

    # Get the modules of all cogs whose directory structure is ./cogs/<module_name>
    for folder in os.listdir("cogs"):
        if not folder.startswith('__'):  # Exclude directories starting with '__'
            bot.load_extension(f"cogs.{folder}")

    @bot.listen()
    async def on_ready():
        assert bot.user is not None
        print("----------------------------------------")
        print(f"{bot.user.name} has connected to Discord!")

    bot.run(config.DISCORD_TOKEN)

if __name__ == "__main__":
    main()
