from nextcord.ext import commands
from transformers import AutoModelForCausalLM, AutoTokenizer
from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import random
import re

# Specify the absolute path for the message database
db_path = "cogs/ai_maid/messages.db"
engine = create_engine(f"sqlite:///{db_path}")
Base = declarative_base()

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, Sequence("message_id_seq"), primary_key=True)
    content = Column(String(250))

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Specify the absolute path for the GIF database
gif_db_path = "cogs/ai_maid/gifs.db"
gif_engine = create_engine(f"sqlite:///{gif_db_path}")
GifBase = declarative_base()

class Gif(GifBase):
    __tablename__ = "gifs"
    id = Column(Integer, Sequence("gif_id_seq"), primary_key=True)
    url = Column(String(250))

GifBase.metadata.create_all(gif_engine)
GifSession = sessionmaker(bind=gif_engine)
gif_session = GifSession()

# Specify the absolute path for the links database
links_db_path = "cogs/ai_maid/links.db"
links_engine = create_engine(f"sqlite:///{links_db_path}")
LinksBase = declarative_base()

class Link(LinksBase):
    __tablename__ = "links"
    id = Column(Integer, Sequence("link_id_seq"), primary_key=True)
    url = Column(String(250))

LinksBase.metadata.create_all(links_engine)
LinksSession = sessionmaker(bind=links_engine)
links_session = LinksSession()

# Load Hugging Face model
model_name = "openai/whisper-large-v3"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

def preprocess_text(text):
    # Remove non-alphanumeric characters and extra spaces
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def is_valid_message(text):
    # Check if the text forms a coherent sentence
    # You can customize this validation logic based on your requirements
    words = text.split()
    if len(words) >= 5:  # Adjust as needed
        return True
    return False

def get_response(prompt):
    # Tokenize the prompt
    input_ids = tokenizer.encode(prompt, return_tensors="pt")

    # Generate AI response
    ai_response = model.generate(
        input_ids=input_ids,
        max_length=150,  # Set maximum length for the response
        pad_token_id=tokenizer.eos_token_id,
        num_return_sequences=1,
        temperature=0.9,  # Adjust temperature for randomness
        repetition_penalty=1.2,  # Adjust repetition penalty as needed
        num_beams=1,  # Set num_beams to 1 for no beam search
        do_sample=True,
    )

    # Decode the response
    response = tokenizer.decode(ai_response[0], skip_special_tokens=True)
    return response

class ConversationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_count = 0
        self.clean_messages_db()

    def cog_unload(self):
        # Perform cleanup tasks if needed
        pass

    async def generate_response(self, channel):
        # Determine whether to respond with a GIF or AI response
        respond_with_gif = random.random() < 0.1  # 10% chance of responding with a GIF

        if respond_with_gif:
            await self.send_random_gif(channel)
        else:
            await self.generate_ai_response(channel)

    async def send_random_gif(self, channel):
        # Get all GIFs from the database
        all_gifs = gif_session.query(Gif).all()

        if all_gifs:
            # Shuffle GIFs to add randomness
            random.shuffle(all_gifs)

            # Choose a random GIF to send
            gif_url = random.choice(all_gifs).url

            # Send GIF to the channel
            await channel.send(gif_url)

    async def generate_ai_response(self, channel):
        # Get all non-empty messages from the database
        all_messages = session.query(Message).filter(Message.content != "").all()

        if all_messages:
            # Shuffle messages to add randomness
            random.shuffle(all_messages)

            # Choose a random message to respond with
            chosen_message = random.choice(all_messages).content

            # Check if the chosen message forms a coherent sentence
            if is_valid_message(chosen_message):
                # Generate AI response based on the chosen message
                ai_response = get_response(chosen_message)

                # Send AI response to the channel
                await channel.send(ai_response)
            else:
                # If the chosen message does not form a coherent sentence, retry
                await self.generate_ai_response(channel)

    def clean_messages_db(self):
        # Clean up messages from bot and specific mentions
        all_messages = session.query(Message).all()
        for message in all_messages:
            if (
                "<@!986747491649224704>" in message.content
            ):  # Replace with your bot's mention ID
                session.delete(message)
            else:
                cleaned_content = preprocess_text(message.content)
                if not cleaned_content:  # If the message is empty after preprocessing
                    session.delete(message)
                else:
                    message.content = cleaned_content
                    session.add(message)
        session.commit()

    def strip_urls(self, content):
        words = content.split()
        non_gif_words = []
        for word in words:
            if word.startswith("https://"):
                if self.contains_gif(word):
                    gif_url = word
                    new_gif = Gif(url=gif_url)
                    gif_session.add(new_gif)
                    gif_session.commit()
                else:
                    new_link = Link(url=word)
                    links_session.add(new_link)
                    links_session.commit()
            else:
                non_gif_words.append(word)
        return " ".join(non_gif_words).strip()

    def contains_gif(self, content):
        # Define your GIF URL patterns or identifiers
        gif_patterns = [
            "tenor.com/view",
            "giphy.com/gifs",
            "media.giphy.com",
        ]  # Example patterns
        return any(pattern in content for pattern in gif_patterns)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # Check if the bot was mentioned
        if self.bot.user.mentioned_in(message):
            await self.generate_response(message.channel)
            return

        # Increment message count after checking direct mention
        self.message_count += 1

        # Only respond every 20 messages unless directly pinged
        if self.message_count % 20 == 0:
            await self.generate_response(message.channel)
            self.message_count = 0  # Reset message count after responding
            return

# Required setup function for the cog
def setup(bot):
    bot.add_cog(ConversationCog(bot))

print("AI Maid Cog Loaded!")
