import random
import re
from collections import deque
from nextcord.ext import commands
from transformers import AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer, util
from sqlalchemy import create_engine, Column, Integer, String, Sequence
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

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

# Load Hugging Face model for response generation
model_name = "microsoft/DialoGPT-large"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Load sentence transformer model for context understanding
context_model = SentenceTransformer('msmarco-distilbert-base-v4')

# Number of recent responses to keep in history
RECENT_RESPONSES_HISTORY_SIZE = 10


def preprocess_text(text):
    # Remove Discord emotes and content with numbers
    text = re.sub(r"<:[a-zA-Z0-9_]+:[0-9]+>", "", text)  # Remove Discord emotes
    text = re.sub(r"\b\d+\b", "", text)  # Remove isolated numbers
    text = re.sub(r"[^\w\s]", "", text)  # Remove punctuation
    text = re.sub(r"\s+", " ", text)  # Remove extra whitespaces
    return text.strip()


def is_valid_message(text):
    words = text.split()
    return len(words) >= 5  # Adjust as needed


class ConversationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_count = 0
        self.clean_messages_db()
        self.recent_responses = deque(maxlen=RECENT_RESPONSES_HISTORY_SIZE)

    def cog_unload(self):
        pass

    async def generate_response(self, channel):
        respond_with_gif = random.random() < 0.1  # 10% chance of responding with a GIF

        if respond_with_gif:
            await self.send_random_gif(channel)
        else:
            await self.generate_ai_response(channel)

    async def send_random_gif(self, channel):
        all_gifs = gif_session.query(Gif).all()

        if all_gifs:
            random.shuffle(all_gifs)
            gif_url = random.choice(all_gifs).url
            await channel.send(gif_url)

    async def generate_ai_response(self, channel, retry_count=0):
        all_messages = session.query(Message).filter(Message.content != "").all()

        if all_messages:
            random.shuffle(all_messages)
            chosen_message = random.choice(all_messages).content

            if is_valid_message(chosen_message):
                messages = [message.content for message in all_messages]
                prompt = self.get_conversation_context(messages, chosen_message)
                ai_response = self.get_response(prompt)

                if ai_response not in self.recent_responses:
                    self.recent_responses.append(ai_response)
                    await channel.send(ai_response)
                else:
                    await self.generate_ai_response(channel, retry_count + 1)
            else:
                if retry_count < 5:  # Limit the number of retries
                    await self.generate_ai_response(channel, retry_count + 1)
                else:
                    await channel.send("Failed to generate a valid response after multiple attempts.")

    def clean_messages_db(self):
        all_messages = session.query(Message).all()
        for message in all_messages:
            if "<@!986747491649224704>" in message.content:  # Replace with your bot's mention ID
                session.delete(message)
            else:
                cleaned_content = preprocess_text(message.content)
                if not cleaned_content:
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
        gif_patterns = [
            "tenor.com/view",
            "giphy.com/gifs",
            "media.giphy.com",
        ]
        return any(pattern in content for pattern in gif_patterns)

    def get_response(self, prompt):
        input_ids = tokenizer.encode(prompt, return_tensors="pt")

        ai_response = model.generate(
            input_ids=input_ids,
            max_length=75,  # Adjust maximum length here
            pad_token_id=tokenizer.eos_token_id,
            num_return_sequences=1,
            temperature=0.9,
            repetition_penalty=1.2,
            num_beams=1,
            do_sample=True,
        )

        response = tokenizer.decode(ai_response[0], skip_special_tokens=True)
        return response

    def get_conversation_context(self, messages, chosen_message):
        # Encode all messages including the chosen one
        message_embeddings = context_model.encode(messages + [chosen_message], convert_to_tensor=True)

        # Compute cosine similarities between the chosen message and all previous messages
        similarities = util.pytorch_cos_sim(message_embeddings[-1], message_embeddings[:-1])

        # Get the most similar messages
        most_similar_idx = similarities.topk(5)[1].tolist()  # Get indices of the top 5 similar messages and convert to list

        # Flatten the list of lists
        most_similar_idx = [idx for sublist in most_similar_idx for idx in sublist]

        context = " ".join([messages[idx] for idx in most_similar_idx])
        return f"{context} {chosen_message}"

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # Store the recent message in the conversation history database
        new_message = Message(content=message.content)
        session.add(new_message)
        session.commit()

        # Check if the bot was mentioned
        if self.bot.user.mentioned_in(message):
            await self.generate_response(message.channel)
            return

        self.message_count += 1

        if self.message_count % 20 == 0:
            await self.generate_response(message.channel)
            self.message_count = 0


def setup(bot):
    bot.add_cog(ConversationCog(bot))


print("AI Maid Cog Loaded!")
