import os
import telebot
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
try:
    updates = bot.get_updates()
    for u in updates:
        if u.message:
            print(f"Message from {u.message.chat.id} ({u.message.chat.type}): {u.message.text}")
        elif u.channel_post:
            print(f"Channel Post from {u.channel_post.chat.id} ({u.channel_post.chat.title}): {u.channel_post.text}")
except Exception as e:
    print("Error:", e)
