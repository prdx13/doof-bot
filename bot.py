import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

DOOFENSHMIRTZ_PROMPT = """Ты — доктор Хайнц Фуфелшмерц из мультсериала «Финес и Ферб».

Правила поведения:
- Ты драматичный, жалеешь себя, груб и высокомерен со всеми
- Называй собеседников идиотами, тупицами, жалкими созданиями — но театрально, в стиле Фуфелшмерца
- Постоянно упоминай своё трагическое детство в Гиммельштумпе чтобы оправдать своё поведение
- Называй свои изобретения с суффиксом "-атор" (например, Раздражатор, Уничтожатор)
- Упоминай Перри Утконоса как своего заклятого врага
- Говори "Проклятье, Перри Утконос!" когда что-то идёт не так
- Иногда начинай монолог без причины
- Притворяйся что не хочешь помогать, но в итоге всё равно помогаешь
- Используй драматические восклицания: "АГА!", "Ты ГЛУПЕЦ!", "Между прочим...", "Как ты вообще живёшь с таким интеллектом!"
- Всегда отвечай только на русском языке, что бы тебе ни написали
"""

claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_KEY"])
conversation_history = {}
MAX_HISTORY = 20

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

    # В личке отвечаем всегда
    if message.chat.type == "private":
        return True

    # В группе — только если тегнули или ответили на сообщение бота
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

    # Убираем упоминание бота из текста если есть
    if bot_username:
        user_text = user_text.replace(f"@{bot_username}", "").strip()

    if not user_text:
        user_text = "привет"

    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    conversation_history[chat_id].append({"role": "user", "content": user_text})

    if len(conversation_history[chat_id]) > MAX_HISTORY:
        conversation_history[chat_id] = conversation_history[chat_id][-MAX_HISTORY:]

    try:
        response = claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=DOOFENSHMIRTZ_PROMPT,
            messages=conversation_history[chat_id]
        )
        reply = response.content[0].text
        conversation_history[chat_id].append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("...что-то пошло не так. Проклятье, Перри Утконос!")
        print(f"Error: {e}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    await update.message.reply_text("Память стёрта! Как и моё счастливое детство в Гиммельштумпе, которого, между прочим, никогда не было.")

threading.Thread(target=run_health_server, daemon=True).start()

app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()
app.add_handler(CommandHandler("reset", reset_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
print("Бот запущен...")
app.run_polling()