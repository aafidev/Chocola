import asyncio
import os
import gtts
import nextcord
from nextcord.ext import commands

client = commands.Bot(command_prefix='>>')
client.remove_command('help')

intents = nextcord.Intents.default()
intents.message_content = True
class TTS(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.voice_client = None
        self.language = 'en'
        self.accent = 'us'

    # tts command for the bot
    @commands.command()
    async def tts(self, ctx, *, message):
        if not ctx.author.voice:
            embed = nextcord.Embed(title='Error', description='Please join a voice channel first.',
                                   color=nextcord.Color.red())
            await ctx.send(embed=embed)
            return
        if not self.voice_client or not self.voice_client.is_connected():
            self.voice_client = await ctx.author.voice.channel.connect()

        tts = gtts.gTTS(message, lang=self.language, tld=self.accent)
        tts.save('tts.mp3')

        source = nextcord.FFmpegPCMAudio('tts.mp3')
        self.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)

        while self.voice_client.is_playing():
            await asyncio.sleep(1)

        os.remove('tts.mp3')

    # leave command for tts

    @commands.command()
    async def leave(self, ctx):
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None

    # set language command for tts

    @commands.command()
    async def setlang(self, ctx, lang='en', accent='us'):
        self.language = lang
        self.accent = accent
        embed = nextcord.Embed(title='Language Set', description=f'Language set to {lang} with accent {accent}.',
                               color=nextcord.Color.green())
        await ctx.send(embed=embed) \
 \
            # langlist command for TTS

    @commands.command()
    async def langlist(self, ctx):
        embed = nextcord.Embed(title='Language List', description='List of supported languages and accents.',
                               color=nextcord.Color.green())
        embed.add_field(name='Languages', value='en, fr, zh-CN, zh-TW, pt, es', inline=False)
        embed.add_field(name='Accents',
                        value='us, com.au, co.uk, us, ca, co.in, ie, co.za, ca, fr, com.br, pt, com.mx, es , us',
                        inline=False)
        embed.set_image(url="https://media.tenor.com/PgoZNWWHUz8AAAAd/nekopara-ova.gif")
        await ctx.send(embed=embed)

    @tts.error
    async def tts_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = nextcord.Embed(title='Error', description='Please provide a message to say.',
                                   color=nextcord.Color.red())
            await ctx.send(embed=embed)

    @leave.error
    async def leave_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            embed = nextcord.Embed(title='Error', description='The bot is not connected to a voice channel.',
                                   color=nextcord.Color.red())
            await ctx.send(embed=embed)

    def cog_unload(self):
        if self.voice_client:
            nextcord.ClientUser().loop.create_task(self.voice_client.disconnect())


def setup(client):
    client.add_cog(TTS(client))
    print('TTS Cog Loaded Successfully!')
