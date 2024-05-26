from nextcord.ext import commands
from transformers import AutoModelForCausalLM, AutoTokenizer
from sqlalchemy import create_engine, Column, Integer, String, Sequence, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import random
import nextcord

# Specify the absolute path for the message database
db_path = 'cogs/ai_maid/messages.db'
engine = create_engine(f'sqlite:///{db_path}')
Base = declarative_base()


class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, Sequence('message_id_seq'), primary_key=True)
    content = Column(String(250))


Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Specify the absolute path for the GIF database
gif_db_path = 'cogs/ai_maid/gifs.db'
gif_engine = create_engine(f'sqlite:///{gif_db_path}')
GifBase = declarative_base()


class Gif(GifBase):
    __tablename__ = 'gifs'
    id = Column(Integer, Sequence('gif_id_seq'), primary_key=True)
    url = Column(String(250))


GifBase.metadata.create_all(gif_engine)
GifSession = sessionmaker(bind=gif_engine)
gif_session = GifSession()

# Specify the absolute path for the links database
links_db_path = 'cogs/ai_maid/links.db'
links_engine = create_engine(f'sqlite:///{links_db_path}')
LinksBase = declarative_base()


class Link(LinksBase):
    __tablename__ = 'links'
    id = Column(Integer, Sequence('link_id_seq'), primary_key=True)
    url = Column(String(250))


LinksBase.metadata.create_all(links_engine)
LinksSession = sessionmaker(bind=links_engine)
links_session = LinksSession()

# Load Hugging Face model
model_name = "microsoft/DialoGPT-medium"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)


def get_response(prompt):
    # Determine response length based on the length of the prompt
    prompt_length = len(prompt.split())
    if prompt_length <= 50:
        response_length = 'short'
    elif prompt_length <= 150:
        response_length = 'medium'
    else:
        response_length = 'long'

    # Define max length based on response length
    if response_length == 'short':
        max_length = 150
    elif response_length == 'medium':
        max_length = 300
    elif response_length == 'long':
        max_length = 500

    # Get AI response
    ai_response = model.generate(
        tokenizer(prompt, return_tensors='pt').input_ids,
        max_length=max_length,
        pad_token_id=tokenizer.eos_token_id,
        num_return_sequences=1,
        temperature=0.9,  # Increase temperature for more randomness
        repetition_penalty=1.2,  # Adjust repetition penalty as needed
        num_beams=1,  # Set num_beams to 1 for no beam search
        do_sample=True
    )
    # Decode the response
    response = tokenizer.decode(ai_response[0], skip_special_tokens=True)
    return response


class ConversationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_count = 0
        self.clean_messages_db()

    def contains_gif(self, content):
        # Define your GIF URL patterns or identifiers
        gif_patterns = ["tenor.com/view", "giphy.com/gifs", "media.giphy.com"]  # Example patterns
        return any(pattern in content for pattern in gif_patterns)

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
        return ' '.join(non_gif_words).strip()

    def clean_messages_db(self):
        # Remove messages containing any URLs from the messages database
        all_messages = session.query(Message).all()
        for message in all_messages:
            cleaned_content = self.strip_urls(message.content)
            if not cleaned_content:  # If the message is empty after stripping URLs
                session.delete(message)
            else:
                message.content = cleaned_content
                session.add(message)
        session.commit()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # Increment message count
        self.message_count += 1

        # Save message to the message database, stripping URLs first
        stripped_content = self.strip_urls(message.content)
        if stripped_content:
            new_message = Message(content=stripped_content)
            session.add(new_message)
            session.commit()

        # Check if bot's mention is present in the message content or if it's the 5th message
        if self.bot.user.mentioned_in(message) or self.message_count % 10 == 0:
            # Decide whether to respond with a GIF or text
            respond_with_gif = random.random() < 0.5  # Adjust the probability here, e.g., 50% chance for GIF

            if respond_with_gif:
                gif = gif_session.query(Gif).order_by(func.random()).first()
                if gif:
                    await message.channel.send(gif.url)
            else:
                # Get AI response based on the last 5 messages
                # Get all messages from the database
                all_messages = session.query(Message).all()

                # Select 5 random messages
                if len(all_messages) >= 5:
                    random_messages = random.sample(all_messages, 5)
                    # Concatenate messages into a single prompt
                    prompt = " ".join(msg.content for msg in random_messages)

                    # Get AI response
                    ai_response = get_response(prompt)

                    # Send AI response to Discord
                    await message.channel.send(ai_response)

# Function to setup cog
def setup(bot):
    bot.add_cog(ConversationCog(bot))
    print("ConversationCog loaded!")
