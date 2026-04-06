import os
import random
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import tasks
import openai
from collections import defaultdict
from datetime import datetime, timedelta

BOT_NAME = "ClarityAI"
TOKEN = os.environ.get("DISCORD_TOKEN")

ai_client = openai.OpenAI(
    base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL"),
    api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = discord.Client(intents=intents)

# --- Participation Tracking ---
participation = defaultdict(int)

# --- Spam Detection ---
user_message_times = defaultdict(list)
SPAM_LIMIT = 5
SPAM_WINDOW = 10  # seconds
warned_users = set()

# --- Bad Words Filter ---
BAD_WORDS = ["spam", "scam", "hate", "abuse"]

# --- Conversation Starters ---
CONVERSATION_STARTERS = [
    "What's something new you've learned this week? Share it with the community!",
    "What's the one tip that completely changed your routine?",
    "What's your biggest challenge right now? Let's help each other out!",
    "What's a product or resource you'd recommend to every beginner here?",
    "What goal are you working towards this month? Drop it below!",
]

# --- Eye Care Tips ---
EYE_CARE_TIPS = [
    "Every 20 minutes, look at something 20 feet away for 20 seconds. Your eyes deserve a break!",
    "Reduce your screen brightness to match the room lighting — it reduces eye strain significantly.",
    "Staying hydrated helps prevent dry eyes. Make sure you're drinking enough water today!",
    "We blink 50% less when looking at screens. Make a conscious effort to blink more often!",
    "Your screen should be at arm's length and slightly below eye level for the most comfortable viewing.",
    "Blue light from screens can disrupt sleep. Try switching to night mode in the evening.",
    "Avoid using your phone in complete darkness — the contrast is harsh on your eyes.",
]


@bot.event
async def on_ready():
    print(f"{BOT_NAME} logged in as {bot.user}")
    spark_conversation.start()
    send_eye_care_tip.start()


@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel
    if channel:
        await channel.send(
            f"Welcome to the community, {member.mention}! I'm **{BOT_NAME}**, your AI community assistant. "
            f"Feel free to ask me anything by mentioning me. We're glad to have you here!"
        )


@tasks.loop(hours=6)
async def spark_conversation():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                starter = random.choice(CONVERSATION_STARTERS)
                await channel.send(f"💬 **Community Check-in:** {starter}")
                break


@tasks.loop(hours=4)
async def send_eye_care_tip():
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                tip = random.choice(EYE_CARE_TIPS)
                await channel.send(f"👁️ **Eye Care Reminder:** {tip}")
                break


async def check_spam(message):
    user_id = message.author.id
    now = datetime.now()
    user_message_times[user_id] = [
        t for t in user_message_times[user_id]
        if now - t < timedelta(seconds=SPAM_WINDOW)
    ]
    user_message_times[user_id].append(now)
    return len(user_message_times[user_id]) >= SPAM_LIMIT


def contains_bad_words(content):
    return any(word in content.lower() for word in BAD_WORDS)


@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    participation[message.author.id] += 1

    if await check_spam(message):
        if message.author.id not in warned_users:
            warned_users.add(message.author.id)
            await message.channel.send(
                f"⚠️ {message.author.mention}, please slow down! You're sending messages too fast."
            )
        try:
            await message.delete()
        except discord.Forbidden:
            pass
        return

    if contains_bad_words(message.content):
        try:
            await message.delete()
        except discord.Forbidden:
            pass
        await message.channel.send(
            f"⚠️ {message.author.mention}, please keep the conversation respectful and safe for everyone."
        )
        return

    if bot.user in message.mentions or isinstance(message.channel, discord.DMChannel):

        if any(word in message.content.lower() for word in ["leaderboard", "top members", "most active"]):
            top = sorted(participation.items(), key=lambda x: x[1], reverse=True)[:5]
            if top:
                leaderboard = "🏆 **Most Active Members:**\n"
                for i, (user_id, count) in enumerate(top, 1):
                    user = bot.get_user(user_id)
                    name = user.display_name if user else f"Member {user_id}"
                    leaderboard += f"{i}. **{name}** — {count} messages\n"
                await message.channel.send(leaderboard)
            else:
                await message.channel.send("No participation data yet. Start chatting!")
import os

if __name__ == "__main__":
    print("Bot is starting...")