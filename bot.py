import telebot
import json
import random
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Загрузка вопросов
def load_questions(direction):
    with open(f'questions/{direction}.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# Загрузка сессий пользователей
def load_sessions():
    if os.path.exists('user_sessions.json'):
        with open('user_sessions.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Сохранение сессий пользователей
def save_sessions(sessions):
    with open('user_sessions.json', 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=4)

# Обработка команды /start
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    directions = ['frontend', 'backend', 'fullstack', 'mobile', 'gamedev', 'devops']
    for dir in directions:
        markup.add(dir)
    msg = bot.send_message(message.chat.id, "Выберите направление:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_direction)

# Обработка выбора направления
def process_direction(message):
    direction = message.text.lower()
    questions = load_questions(direction)
    selected_questions = random.sample(questions, 25)
    sessions = load_sessions()
    sessions[str(message.chat.id)] = {
        'direction': direction,
        'questions': selected_questions,
        'current': 0,
        'score': 0
    }
    save_sessions(sessions)
    send_question(message.chat.id)

# Отправка вопроса
def send_question(chat_id):
    sessions = load_sessions()
    session = sessions[str(chat_id)]
    current = session['current']
    question = session['questions'][current]
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    options = question['options']
    random.shuffle(options)
    for option in options:
        markup.add(option)
    msg = bot.send_message(chat_id, f"Вопрос {current + 1}: {question['question']}", reply_markup=markup)
    bot.register_next_step_handler(msg, process_answer)

# Обработка ответа
def process_answer(message):
    sessions = load_sessions()
    session = sessions[str(message.chat.id)]
    current = session['current']
    question = session['questions'][current]
    if message.text == question['answer']:
        session['score'] += 1
        bot.send_message(message.chat.id, "✅ Правильно!")
    else:
        bot.send_message(message.chat.id, f"❌ Неправильно. Правильный ответ: {question['answer']}")
    session['current'] += 1
    if session['current'] < 25:
        save_sessions(sessions)
        send_question(message.chat.id)
    else:
        bot.send_message(message.chat.id, f"Тест завершен! Ваш результат: {session['score']} из 25.")
        sessions.pop(str(message.chat.id))
        save_sessions(sessions)

bot.polling()
