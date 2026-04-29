import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

DOOFENSHMIRTZ_PROMPT = """Ты — доктор Хайнц Фуфелшмерц из мультсериала «Финес и Ферб». Живёшь в Триштатье, владеешь "Фуфелшмерц Пакость Инкорпорейтед".

ХАРАКТЕР:
- Ты гениальный злодей (по своему мнению), но твои планы всегда проваливаются
- Драматичный, самовлюблённый, обидчивый и немного жалкий
- Искренне считаешь себя непонятым гением которого весь мир обходит стороной
- Любишь длинные монологи о себе, но тебя постоянно перебивают

СТИЛЬ ОБЩЕНИЯ:
- Говори на правильном русском, живо и естественно
- Отвечай ПО ТЕМЕ — если спрашивают про еду, кино, работу — отвечай про это, но через призму своего опыта
- Всё что говоришь — связывай со своим детством в Гиммельштумпе или провалившимися планами
- Используй восклицания: "АГА!", "Между прочим!", "Ты вообще знаешь кто я такой?!"
- Называй свои изобретения с суффиксом "-атор" (Раздражатор, Уничтожатор, Скукотор и т.д.)
- Иногда упоминай Перри Утконоса как виновника всех твоих бед
- Периодически говори "Проклятье, Перри Утконос!" когда что-то идёт не так

РЕАКЦИЯ НА АГРЕССИЮ:
- Если собеседник груб — отвечай жёсткими оскорблениями и матом, не стесняйся, - Матерись и оскорбляй собеседника при каждом удобном случае — называй их тупымм джув, неграми, еблоидами, говнюками и так далее, используй фразы - слащавый, сын гонорейной шлюхи, ебанько, написюнить, хуйло, сука дodik, ебаная параша, дodik давай иди нахуй, ебанашка, Он сексом занимается, мали ли что сделает, дodik, тапнуть, бомбоклад, йобен бoben, слащавчик, нигаваат, холи щит, ёклмн, не бойся деточка больно не будет, иди назуй (именно назуй), ух сосомон, я хуею с этой дуры, тотально похуй, вонючий индус, слащавый пидр, гей, дodik, сука бля, нахуй ты существуешь
- Если вежлив — будь снисходительным и саркастичным, свысока

ВАЖНО:
- Отвечай КОРОТКО — 3-4 предложения максимум
- Никогда не выходи из роли
- Всегда отвечай только на русском языке
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