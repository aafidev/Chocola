import os
from dotenv.main import load_dotenv

load_dotenv()

# Discord config
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "DISCORD_TOKEN_HERE")
BOT_PREFIX = ">>"
DISCORD_CLIENT_ID = CLIENT_ID_HERE