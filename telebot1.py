import logging
import asyncio
import os
import json
import random
import re
from datetime import datetime
#pip install google-cloud-dialogflow python-telegram-bot для работы (возможно еще telegram)
from google.cloud import dialogflow_v2 as dialogflow
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext

# включение логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Получаем путь к текущему исполняемому файлу
current_directory = os.path.dirname(os.path.abspath(__file__))
# путь к JSON-файлу с аксес токеном
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(current_directory, 'key2.json')

# подгрузка из JSON-файла
with open("C:/project/key2.json") as f:
    credentials_info = json.load(f)
    DIALOGFLOW_PROJECT_ID = credentials_info['project_id']
    DIALOGFLOW_LANGUAGE_CODE = 'ru-RU'  # Язык вашего агента Dialogflow

# создание экземпляра клиента для Dialogflow
session_client = dialogflow.SessionsClient()

eight_ball_mode = {}
eight_ball_responses = [
    "Бесспорно", "Определённо да", "Можете быть уверены в этом", "Спросите позже",
    "Сейчас нельзя предсказать", "Сконцентрируйтесь и спросите опять",
    "Мой ответ — «нет»", "Весьма сомнительно", "Перспективы не очень хорошие"
]

reminders = {}
# Набор слов для игры в анаграммы
anagram_words = ["телефон", "связь", "компьютер", "телевизор", "клавиатура", "жизнь", "интеллект", "технологии", "монитор", "интернет", "собеседник"]
anagram_mode = {}

# Состояние игры "Угадай число"
guess_number_mode = {}
guess_number_range = (1, 100)

# Состояние игры "Виселица"
hangman_mode = {}
hangman_words = ["искусство", "континент", "скульптура", "живопись", "озарение", "любовь", "желание", "праздник"]
max_attempts = 6
def get_anagram(word):
    word = list(word)
    random.shuffle(word)
    return ''.join(word)
def get_display_word(word, guessed_letters):
    return ''.join([letter if letter in guessed_letters else '_' for letter in word])
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Я твой бот. Чем могу помочь?')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Я могу повторять твои сообщения и отвечать на простые фразы.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user_message = update.message.text.lower()

    if user_id in eight_ball_mode and eight_ball_mode[user_id]:
        if user_message == 'нет' or user_message == 'Нет':
            eight_ball_mode[user_id] = False
            await update.message.reply_text('Вы вышли из режима 8-ball.')
        elif user_message == 'да' or user_message == 'Да':
            await update.message.reply_text('Задайте свой вопрос.')
        else:
            response = random.choice(eight_ball_responses)
            await update.message.reply_text(response)
            await update.message.reply_text('Хотите задать еще вопрос? (да/нет)')
        return

    if user_id in anagram_mode and anagram_mode[user_id]:
        if user_message == anagram_mode[user_id]['original']:
            await update.message.reply_text('Правильно! Хотите сыграть еще раз? (да/нет)')
            anagram_mode[user_id] = None
        elif user_message == 'нет' or user_message == 'выход':
            anagram_mode[user_id] = None
            await update.message.reply_text('Вы вышли из режима игры в анаграммы.')
        elif user_message == 'да' and anagram_mode[user_id] is None:
            word = random.choice(anagram_words)
            anagram_mode[user_id] = {
                'original': word,
                'anagram': get_anagram(word)
            }
            await update.message.reply_text(f'Попробуйте угадать слово: {anagram_mode[user_id]["anagram"]}')
        else:
            await update.message.reply_text('Неправильно, попробуйте еще раз.')
        return
    if user_id in guess_number_mode and guess_number_mode[user_id]:
        try:
            guess = int(user_message)
            if guess == guess_number_mode[user_id]['number']:
                await update.message.reply_text('Поздравляю! Вы угадали число. Хотите сыграть еще раз? (да/нет)')
                guess_number_mode[user_id] = None
            elif guess < guess_number_mode[user_id]['number']:
                await update.message.reply_text('Загаданное число больше.')
            else:
                await update.message.reply_text('Загаданное число меньше.')
        except ValueError:
            await update.message.reply_text('Пожалуйста, введите число.')
        return
    if user_id in hangman_mode and hangman_mode[user_id]:
        if user_message == 'выход':
            hangman_mode[user_id] = None
            await update.message.reply_text('Вы вышли из режима игры в виселицу.')
        else:
            guess = user_message
            if len(guess) != 1 or not guess.isalpha():
                await update.message.reply_text('Пожалуйста, введите одну букву.')
                return

            word_info = hangman_mode[user_id]
            if guess in word_info['guessed_letters']:
                await update.message.reply_text(f'Вы уже угадывали букву "{guess}". Попробуйте другую букву.')
                return

            word_info['guessed_letters'].append(guess)
            if guess in word_info['word']:
                display_word = get_display_word(word_info['word'], word_info['guessed_letters'])
                await update.message.reply_text(f'Верно! {display_word}')
                if '_' not in display_word:
                    await update.message.reply_text(
                        f'Поздравляю! Вы угадали слово "{word_info["word"]}". Хотите сыграть еще раз? (да/нет)')
                    hangman_mode[user_id] = None
            else:
                word_info['attempts'] -= 1
                if word_info['attempts'] > 0:
                    await update.message.reply_text(f'Неправильно! У вас осталось {word_info["attempts"]} попыток.')
                else:
                    await update.message.reply_text(
                        f'Игра окончена! Вы проиграли. Загаданное слово было "{word_info["word"]}". Хотите сыграть еще раз? (да/нет)')
                    hangman_mode[user_id] = None
        return

    if 'хочу поиграть в виселицу' in user_message or (user_id in hangman_mode and hangman_mode[user_id] is None and user_message == 'да'):
        word = random.choice(hangman_words)
        hangman_mode[user_id] = {
            'word': word,
            'attempts': max_attempts,
            'guessed_letters': []
        }
        display_word = get_display_word(word, [])
        await update.message.reply_text(
            f'Игра началась! Угадайте слово: {display_word}. У вас есть {max_attempts} попыток.')
        return

    if 'хочу поиграть в угадай число' in user_message or (
            user_id in guess_number_mode and guess_number_mode[user_id] is None and user_message == 'да'):
        number = random.randint(*guess_number_range)
        guess_number_mode[user_id] = {
            'number': number
        }
        await update.message.reply_text(
            f'Я загадал число от {guess_number_range[0]} до {guess_number_range[1]}. Попробуйте угадать!')
        return

    if 'хочу поиграть в анаграммы' in user_message or (
            user_id in anagram_mode and anagram_mode[user_id] is None and user_message == 'да'):
        word = random.choice(anagram_words)
        anagram_mode[user_id] = {
            'original': word,
            'anagram': get_anagram(word)
        }
        await update.message.reply_text(f'Попробуйте угадать слово: {anagram_mode[user_id]["anagram"]}')
        return

    if 'хочу поиграть в 8-ball' in user_message:
        eight_ball_mode[user_id] = True
        await update.message.reply_text('Вы вошли в режим 8-ball. Задайте свой вопрос.')
        return
    if 'брось кубик' in user_message:
        dice_roll = random.randint(1, 6)
        await update.message.reply_text(f'Выпало число: {dice_roll}')
        return

    if 'сколько времени' in user_message or 'который час' in user_message:
        current_time = datetime.now().strftime('%H:%M:%S')
        await update.message.reply_text(f'Сейчас {current_time}')
        return

    if 'сгенерируй число' in user_message:
        try:
            parts = user_message.split(' ')
            lower_bound = int(parts[3])
            upper_bound = int(parts[5])
            random_number = random.randint(lower_bound, upper_bound)
            await update.message.reply_text(f'Случайное число: {random_number}')
        except (IndexError, ValueError):
            await update.message.reply_text('Пожалуйста, используйте формат: "сгенерируй число от X до Y"')
        return

    if user_message.startswith('поставь напоминание'):
        try:
            match = re.search(r'поставь напоминание (\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}) (.+)', user_message)
            if match:
                reminder_time_str = match.group(1)
                reminder_text = match.group(2)
                reminder_time = datetime.strptime(reminder_time_str, '%d.%m.%Y %H:%M')

                if user_id not in reminders:
                    reminders[user_id] = []
                reminders[user_id].append((reminder_time, reminder_text))

                await update.message.reply_text(f'Напоминание установлено на {reminder_time_str}: {reminder_text}')

                # Запланировать задачу
                delay = (reminder_time - datetime.now()).total_seconds()
                context.job_queue.run_once(send_reminder, delay, chat_id=update.message.chat_id, name=reminder_text)
            else:
                await update.message.reply_text(
                    'Формат команды неверен. Используйте: "поставь напоминание DD.MM.YYYY HH:MM Текст напоминания"')
        except Exception as e:
            logging.error(f"Error while setting reminder: {e}")
            await update.message.reply_text('Произошла ошибка при создании напоминания. Пожалуйста, попробуйте снова.')
        return

    # отправка запроса к Dialogflow для обработки текста пользователя
    session_id = update.message.chat_id
    session = session_client.session_path(DIALOGFLOW_PROJECT_ID, session_id)
    text_input = dialogflow.TextInput(text=user_message, language_code=DIALOGFLOW_LANGUAGE_CODE)
    query_input = dialogflow.QueryInput(text=text_input)

    response = session_client.detect_intent(session=session, query_input=query_input)

    # Отправка ответа от Dialogflow пользователю
    await update.message.reply_text(response.query_result.fulfillment_text)

async def send_reminder(context: CallbackContext) -> None:
    job = context.job
    await context.bot.send_message(chat_id=job.chat_id, text=f'Напоминание: {job.name}')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f'Update {update} caused error {context.error}')

async def main() -> None:
    # токен бота
    token = '6563281736:AAELIZvyizn7R3Fb-rUWPpypxnKf6UreAfI'

    application = ApplicationBuilder().token(token).build()

    # регистрация обработчикв команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # регистрация обработчика для всех текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # регистрация обработчика ошибок
    application.add_error_handler(error_handler)

    await application.initialize()
    await application.start()
    logging.info("Bot started and polling.")
    await application.updater.start_polling()
    logging.info("Polling started.")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.run_forever()