import nextcord
from nextcord.ext import commands

intents = nextcord.Intents.default()
intents.message_content = True


class Invite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # If the user types >>invite, the bot will generate an invite link for itself
    @nextcord.slash_command(name="invite", description="Invite Chocola to your server!")
    async def invite(self, ctx):
        embed = nextcord.Embed(
            title="Invite Link:",
            description="https://discord.com/oauth2/authorize?client_id=986747491649224704&scope=bot&permissions=1095199752191",
            color=nextcord.Color.green(),
        )
        # It will also show the number of servers the bot is currently in
        embed.add_field(name="Servers:", value=f"{len(self.bot.guilds)}", inline=True)
        # It will also show the number of users the bot can see
        embed.add_field(name="Users:", value=f"{len(self.bot.users)}", inline=True)
        # It will also show the shards the bot is currently using
        embed.add_field(name="Shards:", value=f"{self.bot.shard_count}", inline=True)
        # It will also show the number of commands the bot has
        embed.add_field(
            name="Commands:", value=f"{len(self.bot.commands)}", inline=True
        )
        # set footer to the bot name and avatar
        embed.set_footer(
            text=f"{self.bot.user.name}", icon_url=f"{self.bot.user.avatar.url}"
        )
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Invite(bot))
    print("Invite Cog Loaded Successfully!")
