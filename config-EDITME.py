import os
from dotenv.main import load_dotenv

load_dotenv()

# Discord config
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "EDITME")
BOT_PREFIX = ">>"
DISCORD_CLIENT_ID = EDITME
