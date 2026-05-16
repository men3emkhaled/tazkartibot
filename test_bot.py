import os
import telebot
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
print(f"Testing sending to: {TELEGRAM_CHAT_ID}")
try:
    bot.send_message(TELEGRAM_CHAT_ID, "🧪 Test Message from System")
    print("Success")
except Exception as e:
    print("Error:", e)
