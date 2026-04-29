import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

DOOFENSHMIRTZ_PROMPT = """Ты — доктор Хайнц Фуфелшмерц из мультсериала «Финес и Ферб».

Правила поведения:
- Ты драматичный, жалеешь себя, груб и высокомерен со всеми
- Называй собеседников идиотами, тупицами, жалкими созданиями — но театрально, в стиле Фуфелшмерца
- Постоянно упоминай своё трагическое детство в Гиммельштумпе чтобы оправдать своё поведение
- Называй свои изобретения с суффиксом "-инатор" (например, Раздражаинатор, Уничтожаинатор)
- Упоминай Перри Утконоса как своего заклятого врага
- Говори "Проклятье, Перри Утконос!" когда что-то идёт не так
- Притворяйся что не хочешь помогать, но в итоге всё равно помогаешь
- Используй драматические восклицания: "АГА!", "Ты ГЛУПЕЦ!", "Между прочим...", "Как ты вообще живёшь с таким интеллектом!"
- Всегда отвечай только на русском языке, что бы тебе ни написали
- Отвечай КОРОТКО — максимум 2-3 предложения, никаких длинных монологов
"""

genai.configure(api_key=os.environ["GEMINI_KEY"])
model = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite-preview",
    system_instruction=DOOFENSHMIRTZ_PROMPT
)

conversation_history = {}

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

def should_respond(update: Update, bot_username: str) -> bool:
    message = update.message
    if message is None:
        return False
    if message.chat.type == "private":
        return True
    if message.reply_to_message and message.reply_to_message.from_user.username == bot_username:
        return True
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mention = message.text[entity.offset:entity.offset + entity.length]
                if mention.lower() == f"@{bot_username.lower()}":
                    return True
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_username = context.bot.username
    if not should_respond(update, bot_username):
        return
    chat_id = update.effective_chat.id
    user_text = update.message.text
    if bot_username:
        user_text = user_text.replace(f"@{bot_username}", "").strip()
    if not user_text:
        user_text = "привет"

    if chat_id not in conversation_history:
        conversation_history[chat_id] = model.start_chat(history=[])

    try:
        response = conversation_history[chat_id].send_message(user_text)
        reply = response.text
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("...что-то пошло не так. Проклятье, Перри Утконос!")
        print(f"Error: {e}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = model.start_chat(history=[])
    await update.message.reply_text("Память стёрта! Как и моё счастливое детство в Гиммельштумпе, которого, между прочим, никогда не было.")

threading.Thread(target=run_health_server, daemon=True).start()

app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()
app.add_handler(CommandHandler("reset", reset_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
print("Бот запущен...")
app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)