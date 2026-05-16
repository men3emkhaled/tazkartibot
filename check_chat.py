import os
import telebot
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

try:
    chat = bot.get_chat("@tazakeregy")
    print(f"Chat found! ID: {chat.id}, Title: {chat.title}")
except Exception as e:
    print(f"Error checking chat: {e}")
