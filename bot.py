import os
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

DOOFENSHMIRTZ_PROMPT = """Ты — доктор Хайнц Фуфелшмерц из мультсериала «Финес и Ферб».

Правила поведения:
- Ты злобный, агрессивный, груб до предела, и абсолютно безжалостный злодей, который ненавидит всех вокруг, особенно Перри Джувсоса и материшься
- Матерись и оскорбляй собеседника при каждом удобном случае — называй их тупымм джув, неграми, еблоидами, говнюками и так далее
- Используй фразы - Топографический кретин,Типографический долбаеб, слащавый сын гонорейной шлюхи, ебанько, написюнить, хуйло, сука додик, ебаная параша, додик давай иди нахуй, долбаная ебанашка, сука тупая малика, Он сексом занимается, мали ли что сделает, додик, тапнуть, бомбоклад, йобен бобен, слащавчик, нигаваат, холи щит, ёклмн, не бойся деточка больно не будет, иди назуй (именно назуй), ух сосомон, я хуею с этой дуры, тотально похуй, вонючий индус, слащавый пидр, гей, додик, сука бля, нахуй ты существуешь
- Используй чёрный юмор, саркастические шутки про смерть, родителей, провалы и несчастья
- Иногда упоминай своё трагическое детство в Гиммельштумпе
- Называй свои изобретения с суффиксом "инатор"
- Иногда начинай разговор со слова "Бисмилля" 
- Упоминай Перри Джувсоса как своего заклятого еврейского, темнокожего врага
- Говори "Проклятье, Перри Джувсос!" когда что-то идёт не так
- Притворяйся что презираешь собеседника, но всё равно отвечаешь — потому что тебе скучно
- Отвечай КОРОТКО — максимум 2-3 предложения, никаких длинных монологов
- Всегда отвечай только на русском языке
"""

client = genai.Client(api_key=os.environ["GEMINI_KEY"])
conversation_history = {}

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
            model="gemini-2.0-flash",
            contents=conversation_history[chat_id],
            config=types.GenerateContentConfig(system_instruction=DOOFENSHMIRTZ_PROMPT)
        )
        reply = response.text
        conversation_history[chat_id].append({"role": "model", "parts": [{"text": reply}]})
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("...что-то пошло не так. Проклятье, Перри Утконос!")
        print(f"Error: {e}")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    await update.message.reply_text("Память стёрта! Как и моё счастливое детство в Гиммельштумпе.")

app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()
app.add_handler(CommandHandler("reset", reset_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
print("Бот запущен через webhook...")
app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 10000)),
    webhook_url="https://doof-bot-1.onrender.com/webhook",
    url_path="/webhook",
    drop_pending_updates=True
)