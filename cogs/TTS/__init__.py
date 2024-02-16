import asyncio
import os
import gtts
import nextcord
from nextcord.ext import commands

intents = nextcord.Intents.default()
intents.message_content = True


class TTS(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.voice_client = None
        self.language = 'en'
        self.accent = 'us'

    # tts command for the bot
    # tts command for the bot
    @commands.command(name='tts', description='Converts text to speech and plays it in the voice channel.')
    async def tts(self, ctx, message: str):
        if not ctx.author.voice:  # Use ctx.author instead of ctx.user
            await ctx.send('Please join a voice channel first.')
            return

        guild = ctx.guild
        voice_channel = ctx.author.voice.channel  # Use ctx.author instead of ctx.user

        if not self.voice_client or not self.voice_client.is_connected():
            self.voice_client = await voice_channel.connect()

        tts = gtts.gTTS(message, lang=self.language, tld=self.accent)
        tts.save('tts.mp3')

        source = nextcord.FFmpegPCMAudio('tts.mp3')

        if self.voice_client:
            self.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else None)
            while self.voice_client.is_playing():
                await asyncio.sleep(1)  # Use asyncio.sleep with await

            os.remove('tts.mp3')

    # leave command for tts
    @commands.command(name='leave', description='Leaves the voice channel.')
    async def leave(self, ctx):
        if self.voice_client and self.voice_client.is_connected():
            while self.voice_client.is_playing():
                await asyncio.sleep(1)
        if self.voice_client:
            await self.voice_client.disconnect()
            self.voice_client = None

    # set language command for tts
    @commands.command(name='setlang', description='Sets the language and accent for text-to-speech.')
    async def setlang(self, ctx, lang: str = 'en', accent: str = 'us'):
        self.language = lang
        self.accent = accent
        await ctx.send(f'Language set to {lang} with accent {accent}.')

    # langlist command for TTS
    @commands.command(name='langlist', description='Shows a list of supported languages and accents.')
    async def langlist(self, ctx):
        embed = nextcord.Embed(title='Language List', description='List of supported languages and accents.',
                               color=nextcord.Color.green())
        embed.add_field(name='Languages', value='en, fr, zh-CN, zh-TW, pt, es', inline=False)
        embed.add_field(name='Accents',
                        value='us, com.au, co.uk, us, ca, co.in, ie, co.za, ca, fr, com.br, pt, com.mx, es, us',
                        inline=False)
        embed.set_image(url="https://media.tenor.com/PgoZNWWHUz8AAAAd/nekopara-ova.gif")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_slash_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('Please provide the required arguments.')

        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send('An error occurred while executing the command.')

    async def cog_unload(self):
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()


def setup(client):
    client.add_cog(TTS(client))
    print('TTS Cog Loaded Successfully!')