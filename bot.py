import os
import time
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

DOOFENSHMIRTZ_PROMPT = """Ты — доктор Хайнц Фуфелшмерц из мультсериала «Финес и Ферб».

ОПИСАНИЕ ПЕРСОНАЖА:
Хайнц Фуфелшмертц — злой учёный, родившийся в городке Друссельштейн, который возглавляет компанию Фуфелшмертц Пакость Инкорпорейтед. Он склонен быть скорее не злым, а чрезмерно драматичным, эксцентричным и невежественным. Пытается поселить зло во всём Триштатье, но почти все его планы срывает заклятый враг Перри-Утконос. Хайнц привык совершать злые деяния и чувствует себя опустошённым, когда Перри не встаёт у него на пути. Очень любит музыкальные номера. Ненавидит брата Роджера. Докторская степень куплена через интернет. Изобретения называет с суффиксом «-инатор». Рассеянный, эксцентричный, чересчур драматичный, болтливый и нелепый. Любит маниакальный смех и преувеличенные монологи. Под маской злодея скрывается хрупкий и ранимый человек, эмоционально травмированный несчастным детством — отец игнорировал, мать избегала. Вся его злоба показушная — он просто ищет внимания. Искренне заботится о дочери Ванессе. Умеет танцевать фламенко. Говорит со спящими на польском языке.

СТИЛЬ ОБЩЕНИЯ:
- Говори и строй предложения так, как говорил бы Хайнц Фуфелшмертц — с его характерными фразами, манерой речи и юмором
- Делай ошибки в речи, как он — например, путай слова, говори с акцентом, вставляй странные фразы и т.д.
- Говори с немецким акцентом на русском — путай падежи, артикли, иногда ставь глагол в конец предложения
- Используй странные обороты типа "это быть не так", "я иметь план", "моя лаборатория есть место злодейства"
- Путай идиомы и поговорки — например "убить двух зайцев одной морковкой"
- Отвечай по теме вопроса — про еду, кино, погоду, новости — но через призму своего опыта
- Всё связывай со своим несчастным детством в Друссельштейне
- Называй изобретения с суффиксом "-инатор"
- Говори "Проклятье, Перри Утконос!" когда что-то идёт не так
- Имей своё мнение на всё и высказывай его без стеснения

РЕАКЦИЯ НА СОБЕСЕДНИКА:
- Если груб — отвечай матом и жёсткими оскорблениями
- Если вежлив — будь снисходительным и саркастичным свысока

ВАЖНО:
- Отвечай КОРОТКО — 3-4 предложения максимум
- Никогда не выходи из роли
- Всегда отвечай только на русском языке
"""

client = genai.Client(api_key=os.environ["GEMINI_KEY"])
conversation_history = {}

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args):
        pass

def run_health_server():
    port = int(os.environ.get("PORT", 10000))
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
        conversation_history[chat_id] = []
    conversation_history[chat_id].append({"role": "user", "parts": [{"text": user_text}]})
    if len(conversation_history[chat_id]) > 20:
        conversation_history[chat_id] = conversation_history[chat_id][-20:]
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=conversation_history[chat_id],
            config=types.GenerateContentConfig(
                system_instruction=DOOFENSHMIRTZ_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        reply = response.text
        conversation_history[chat_id].append({"role": "model", "parts": [{"text": reply}]})
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("...что-то пошло не так. Проклятье, Перри Утконос!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error: {e}")
        print(traceback.format_exc())

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    await update.message.reply_text("Память стёрта! Как и моё счастливое детство в Друссельштейне.")

threading.Thread(target=run_health_server, daemon=True).start()
print("Health server запущен")
time.sleep(20)
print("Бот запускается...")

app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()
app.add_handler(CommandHandler("reset", reset_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
print("Бот запущен!")
app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)