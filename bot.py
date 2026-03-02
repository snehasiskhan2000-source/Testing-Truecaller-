import telebot
import requests
import os
from flask import Flask
import threading

# 🔑 SECRETS (Loaded safely from Render Environment Variables)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TC_BEARER = os.environ.get("TC_BEARER")

if not BOT_TOKEN or not TC_BEARER:
    raise ValueError("Missing BOT_TOKEN or TC_BEARER environment variables!")

bot = telebot.TeleBot(BOT_TOKEN)

MASTER_KEY = "AyushloveAyushi"
VALID_KEYS = {"USER_1", "USER_2"}

TC_URL = "https://search5-noneu.truecaller.com/v2/search"
TC_HEADERS = {
    "User-Agent": "Truecaller/16.7.8 (Android;15)",
    "Accept": "application/json",
    "Accept-Encoding": "identity",
    "authorization": f"Bearer {TC_BEARER}"
}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 Welcome to the Lookup Bot!\n\n"
        "Usage:\n`/lookup <key> <number>`\n\n"
        "Example:\n`/lookup USER_1 9876543210`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['lookup'])
def handle_lookup(message):
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ Missing parameters.\nUsage: `/lookup <key> <number>`", parse_mode="Markdown")
        return

    key, number = args[1], args[2]

    if key != MASTER_KEY and key not in VALID_KEYS:
        bot.reply_to(message, "🚫 Access Denied: Invalid key.")
        return

    processing_msg = bot.reply_to(message, f"🔍 Searching for `{number}`...", parse_mode="Markdown")

    try:
        r = requests.get(
            TC_URL,
            params={"q": number, "countryCode": "IN", "type": 4, "encoding": "json"},
            headers=TC_HEADERS,
            timeout=10
        )

        if r.status_code != 200 or not r.text.strip():
            bot.edit_message_text(f"❌ Upstream blocked or empty (HTTP {r.status_code})", chat_id=message.chat.id, message_id=processing_msg.message_id)
            return

        raw = r.json()
        if not raw.get("data"):
            bot.edit_message_text("⚠️ No results found.", chat_id=message.chat.id, message_id=processing_msg.message_id)
            return

        response_text = "✅ **Lookup Results:**\n\n"
        for d in raw.get("data", []):
            phone = (d.get("phones") or [{}])[0]
            addr = (d.get("addresses") or [{}])[0]
            mail = (d.get("internetAddresses") or [{}])[0]

            response_text += (
                f"👤 **Name:** {d.get('name', 'N/A')}\n"
                f"⚧️ **Gender:** {d.get('gender', 'N/A')}\n"
                f"📱 **Carrier:** {phone.get('carrier', 'N/A')}\n"
                f"🏙️ **City:** {addr.get('city', 'N/A')}\n"
                f"📧 **Email:** {mail.get('id', 'N/A')}\n"
                f"🚨 **Fraud/Spam:** {'Yes 🛑' if d.get('isFraud') else 'No 🟢'}\n"
                "------------------------\n"
            )

        bot.edit_message_text(response_text, chat_id=message.chat.id, message_id=processing_msg.message_id, parse_mode="Markdown")

    except Exception as e:
        bot.edit_message_text(f"❌ An error occurred: {str(e)}", chat_id=message.chat.id, message_id=processing_msg.message_id)

# --- DUMMY FLASK SERVER FOR RENDER ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running beautifully!"

def run_flask():
    # Render assigns a port dynamically via the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Start the Flask web server in a background thread
    threading.Thread(target=run_flask).start()
    
    print("🤖 Bot is polling Telegram...")
    bot.infinity_polling()
  
