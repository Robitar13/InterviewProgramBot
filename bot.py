import telebot
import json
import os
import random

TOKEN = os.getenv("TELEGRAM_TOKEN")  # Или вставь свой токен напрямую, если тестируешь локально
bot = telebot.TeleBot(8162107934:AAFI7VCgfRZjBCwAOsZK_2SE-TvqQDwgkFY)

DATA_DIR = "data"
SESSIONS_FILE = "user_sessions.json"
QUESTIONS_PER_TEST = 25

# Загрузка сессий
if os.path.exists(SESSIONS_FILE):
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        user_sessions = json.load(f)
else:
    user_sessions = {}

# --- Команда /start ---
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

    bot.send_message(chat_id, "Привет! Выбери направление для собеседования:", reply_markup=markup)


# --- Выбор направления ---
@bot.message_handler(func=lambda msg: msg.text.lower() in [f.replace(".json", "") for f in os.listdir(DATA_DIR)])
def handle_role_selection(message):
    chat_id = str(message.chat.id)
    role = message.text.lower()
    filepath = os.path.join(DATA_DIR, f"{role}.json")

    with open(filepath, "r", encoding="utf-8") as f:
        all_questions = json.load(f)

    # Фильтрация ранее использованных
    used = user_sessions[chat_id]["used_questions"]
    available = [q for q in all_questions if q["question"] not in used]

    if len(available) < QUESTIONS_PER_TEST:
        # Если закончились, сбрасываем
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


# --- Задание вопроса ---
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


# --- Обработка ответа ---
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


# --- Завершение теста ---
def finish_test(chat_id):
    session = user_sessions[chat_id]
    total = len(session["questions"])
    score = session["score"]
    percent = round((score / total) * 100)

    if percent >= 80:
        feedback = "🎉 Ты бы точно прошёл собеседование!"
    elif percent >= 50:
        feedback = "🧐 Результат средний, есть куда расти."
    else:
        feedback = "😕 Пока не прошёл бы. Но ты можешь попробовать снова!"

    bot.send_message(chat_id, f"📊 Результат: {score} из {total} ({percent}%)\n{feedback}")
    bot.send_message(chat_id, "Хочешь пройти собеседование ещё раз? Напиши /start")

    # Сохраняем сессии
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(user_sessions, f, ensure_ascii=False, indent=2)


# --- Запуск бота ---
bot.polling()
