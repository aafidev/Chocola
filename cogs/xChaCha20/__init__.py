import nextcord
from nextcord.ext import commands
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import os
import base64
import asyncio
import io


class EncryptionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.decryption_attempts = {}

    @commands.command()
    async def encrypt(self, ctx, *, content):
        encryption_key, encrypted_text = self.encrypt_text(content)
        encrypted_file = self.save_text_to_file(encrypted_text)
        key_file = self.save_key_to_file(encryption_key)
        await ctx.send("Encryption Successful.")
        await ctx.author.send("Here is your encryption key:")
        await ctx.author.send(encryption_key)
        await ctx.author.send(file=nextcord.File(key_file))
        await ctx.author.send(file=nextcord.File(encrypted_file))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        if isinstance(message.channel, nextcord.DMChannel):
            user = message.author
            if user.id in self.decryption_attempts:
                if "key" not in self.decryption_attempts[user.id]:
                    decryption_key = message.content.strip()
                    self.decryption_attempts[user.id]["key"] = decryption_key
                    await self.decryption_attempts[user.id]["event"].set()
                elif "file" not in self.decryption_attempts[user.id]:
                    self.decryption_attempts[user.id]["file"] = message.attachments[0]
                    await self.decryption_attempts[user.id]["event"].set()

    @commands.command()
    async def decrypt(self, ctx, decryption_key=None, *, encrypted_text=None):
        if not decryption_key:
            decryption_key = await self.prompt_decryption_key(ctx.author)

        if not decryption_key:
            await ctx.send("No decryption key provided.")
            return

        if not encrypted_text:
            await ctx.send("No encrypted text provided.")
            return

        decrypted_text = await self.decrypt_text(encrypted_text, decryption_key)
        if decrypted_text:
            await ctx.author.send("Decryption Successful.")
            await ctx.author.send("Decrypted Text:")
            await ctx.author.send(decrypted_text)
        else:
            await ctx.author.send("Decryption failed. Invalid key or encrypted text.")

    async def prompt_decryption_key(self, user):
        attempts = self.decryption_attempts.get(user.id, {}).get("attempts", 0)
        if attempts >= 3:
            return None

        self.decryption_attempts[user.id] = {
            "attempts": attempts + 1,
            "event": asyncio.Event(),
        }
        await user.send("Please enter the decryption key:")

        await self.decryption_attempts[user.id]["event"].wait()
        decryption_key = self.decryption_attempts[user.id].get("key")
        self.decryption_attempts.pop(user.id, None)
        return decryption_key

    def encrypt_text(self, text):
        key = ChaCha20Poly1305.generate_key()
        cipher = ChaCha20Poly1305(key)
        nonce = os.urandom(12)
        encrypted_data = cipher.encrypt(nonce, text.encode("utf-8"), None)
        encryption_key = base64.b64encode(key).decode("utf-8")
        return encryption_key, f"{nonce.hex()}\n{encrypted_data.hex()}"

    async def decrypt_text(self, encrypted_text, decryption_key):
        key = base64.b64decode(decryption_key)
        cipher = ChaCha20Poly1305(key)
        encrypted_text_parts = encrypted_text.split("\n")
        nonce = bytes.fromhex(encrypted_text_parts[0])
        encrypted_data = bytes.fromhex(encrypted_text_parts[1])
        try:
            decrypted_data = cipher.decrypt(nonce, encrypted_data, None)
        except Exception as e:
            print(e)
            return None

        if decrypted_data:
            return decrypted_data.decode("utf-8")
        else:
            return None

    def save_text_to_file(self, text):
        file_path = "encrypted_text.txt"
        with open(file_path, "w") as file:
            file.write(text)
        return file_path

    def save_key_to_file(self, key):
        file_path = "encryption_key.txt"
        with open(file_path, "w") as file:
            file.write(key)
        return file_path


def setup(bot):
    bot.add_cog(EncryptionCog(bot))


print("Encryption Cog loaded.")
