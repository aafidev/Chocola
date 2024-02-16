import os
from dotenv.main import load_dotenv

load_dotenv()

# Discord config
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "editme")
BOT_PREFIX = ">>"
DISCORD_CLIENT_ID = 986747491649224704
