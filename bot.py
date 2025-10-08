import os
import json
#import random
#import telebot

# Загружаем токен из переменной окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise Exception("❌ TELEGRAM_TOKEN не найден. Убедитесь, что он добавлен в GitHub Secrets!")

bot = telebot.TeleBot(TOKEN)

# Константы
DATA_DIR = "data"
SESSIONS_FILE = "user_sessions.json"
QUESTIONS_PER_TEST = 25

# Загружаем сессии пользователей
if os.path.exists(SESSIONS_FILE):
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        user_sessions = json.load(f)
else:
    user_sessions = {}

# Команда /start — выбор направления
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = str(message.chat.id)
    user_sessions[chat_id] = {
        "role": None,
        "questions": [],
        "used_questions": [],
        "step": 0,
        "score": 0
    }

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for file in os.listdir(DATA_DIR):
        if file.endswith(".json"):
            name = file.replace(".json", "").capitalize()
            markup.add(name)

    bot.send_message(chat_id, "👋 Привет! Выбери направление для собеседования:", reply_markup=markup)

# Обработка выбора направления
@bot.message_handler(func=lambda msg: msg.text.lower() in [f.replace(".json", "") for f in os.listdir(DATA_DIR)])
def handle_role_selection(message):
    chat_id = str(message.chat.id)
    role = message.text.lower()
    filepath = os.path.join(DATA_DIR, f"{role}.json")

    with open(filepath, "r", encoding="utf-8") as f:
        all_questions = json.load(f)

    used = user_sessions[chat_id]["used_questions"]
    available = [q for q in all_questions if q["question"] not in used]

    if len(available) < QUESTIONS_PER_TEST:
        available = all_questions
        user_sessions[chat_id]["used_questions"] = []

    selected = random.sample(available, QUESTIONS_PER_TEST)

    user_sessions[chat_id].update({
        "role": role,
        "questions": selected,
        "step": 0,
        "score": 0
    })

    ask_question(chat_id)

# Задаёт вопрос
def ask_question(chat_id):
    session = user_sessions[chat_id]
    step = session["step"]

    if step >= len(session["questions"]):
        return finish_test(chat_id)

    q = session["questions"][step]
    options_text = "\n".join([f"{chr(65+i)}) {opt}" for i, opt in enumerate(q["options"])])
    question_text = f"❓ Вопрос {step+1}/{QUESTIONS_PER_TEST}:\n<b>{q['question']}</b>\n\n{options_text}"

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for i in range(len(q["options"])):
        markup.add(chr(65+i))

    bot.send_message(chat_id, question_text, parse_mode="HTML", reply_markup=markup)

# Обработка ответа пользователя
@bot.message_handler(func=lambda msg: msg.text.upper() in ["A", "B", "C", "D", "E"])
def handle_answer(message):
    chat_id = str(message.chat.id)
    session = user_sessions.get(chat_id)

    if not session:
        return bot.send_message(chat_id, "Пожалуйста, начни с команды /start")

    step = session["step"]
    q = session["questions"][step]
    correct_index = q["answer"]
    correct_letter = chr(65 + correct_index)

    if message.text.upper() == correct_letter:
        bot.send_message(chat_id, "✅ Верно!")
        session["score"] += 1
    else:
        correct_answer_text = q["options"][correct_index]
        bot.send_message(chat_id, f"❌ Неверно. Правильный ответ: {correct_letter}) {correct_answer_text}")

    session["used_questions"].append(q["question"])
    session["step"] += 1
    ask_question(chat_id)

# Завершение собеседования
def finish_test(chat_id):
    session = user_sessions[chat_id]
    total = len(session["questions"])
    score = session["score"]
    percent = round((score / total) * 100)

    if percent >= 80:
        feedback = "🎉 Отлично! Ты бы точно прошёл собеседование!"
    elif percent >= 50:
        feedback = "🧐 Неплохо, но стоит немного подтянуть знания."
    else:
        feedback = "😕 Пока не прошёл бы. Но ты можешь попробовать ещё раз!"

    bot.send_message(chat_id, f"📊 Результат: {score} из {total} ({percent}%)\n{feedback}")
    bot.send_message(chat_id, "Хочешь пройти ещё раз? Напиши /start")

    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_sessions, f, ensure_ascii=False, indent=2)

# Запуск бота
bot.polling()
