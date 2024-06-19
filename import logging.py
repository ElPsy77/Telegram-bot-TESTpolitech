import logging
import random
import docx
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Включение логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Функция для чтения вопросов из .docx файла и перемешивания ответов
def read_questions_from_docx(docx_filename):
    try:
        doc = docx.Document(docx_filename)
    except Exception as e:
        logger.error(f"Ошибка при открытии документа '{docx_filename}': {e}")
        return []

    questions = []
    question_text = ""
    options = {}
    correct_answer = ""

    for para in doc.paragraphs:
        text = para.text.strip()
        if text.startswith("ANSWER:"):
            correct_answer = text.replace("ANSWER:", "").strip()
            if question_text and options:
                # Перемешивание ответов
                option_items = list(options.items())
                random.shuffle(option_items)
                options = dict(option_items)

                # Обновление правильного ответа после перемешивания
                for key, value in options.items():
                    if value == correct_answer:
                        correct_answer = key

                questions.append({
                    "question": question_text.strip(),
                    "options": options,
                    "answer": correct_answer
                })
                # Добавление отладочной информации
                logger.info(f"Вопрос добавлен: {question_text.strip()}")
                logger.info(f"Варианты ответов: {options}")
                logger.info(f"Правильный ответ: {correct_answer}")

            question_text = ""
            options = {}
            correct_answer = ""
        elif text[:2] in ["A.", "B.", "C.", "D.", "E."]:
            option, answer_text = text.split(".", 1)
            options[option.strip()] = answer_text.strip()
        else:
            if question_text:
                question_text += "\n"
            question_text += text

    # Проверка последнего вопроса, если файл не заканчивается на "ANSWER:"
    if question_text and options and correct_answer:
        questions.append({
            "question": question_text.strip(),
            "options": options,
            "answer": correct_answer
        })
        # Добавление отладочной информации
        logger.info(f"Последний вопрос добавлен: {question_text.strip()}")
        logger.info(f"Варианты ответов: {options}")
        logger.info(f"Правильный ответ: {correct_answer}")

    return questions

# Функция для старта викторины
async def start_quiz(update: Update, context: CallbackContext, hardcore=False):
    user_data = context.user_data
    if 'questions' not in user_data or not user_data['questions']:
        await update.message.reply_text("Вопросы не найдены. Пожалуйста, отправьте документ с вопросами. /help")
        return

    questions = user_data['questions']
    if not hardcore:
        num_questions = min(len(questions), 50)
        random.shuffle(questions)
        user_data['selected_questions'] = questions[:num_questions]
    else:
        user_data['selected_questions'] = questions
    user_data['current_question'] = 0
    user_data['correct_answers'] = 0

    await ask_question(update, context)

# Функция для задавания вопросов
async def ask_question(update: Update, context: CallbackContext):
    user_data = context.user_data
    current_question = user_data['current_question']
    question = user_data['selected_questions'][current_question]

    options_text = "\n".join([f"{opt}. {txt}" for opt, txt in question['options'].items()])
    reply_markup = ReplyKeyboardMarkup(
        [['A', 'B'], ['C', 'D'], ['E']], one_time_keyboard=True, resize_keyboard=True
    )

    await update.message.reply_text(
        f"Вопрос {current_question + 1}:\n{question['question']}\n\nВарианты ответов:\n{options_text}\n\nВаш ответ (укажите букву варианта ответа):",
        reply_markup=reply_markup
    )

# Функция для обработки ответов
async def handle_answer(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_answer = update.message.text.strip().upper()
    current_question = user_data['current_question']
    question = user_data['selected_questions'][current_question]

    if user_answer == question['answer']:
        await update.message.reply_text(
            "Верно! В том же духе!\nВведите /startquiz чтобы начать викторину или /startquiz_hardcore для режима хардкор.",
            reply_markup=ReplyKeyboardRemove()
        )
        user_data['correct_answers'] += 1
    else:
        await update.message.reply_text(
            f"Неверно. Правильный ответ: {question['answer']}\nТы сможешь!\nВведите /startquiz чтобы начать викторину или /startquiz_hardcore для режима хардкор.",
            reply_markup=ReplyKeyboardRemove()
        )

    user_data['current_question'] += 1
    if user_data['current_question'] < len(user_data['selected_questions']):
        await ask_question(update, context)
    else:
        await update.message.reply_text(
            f"Викторина завершена! Вы ответили правильно на {user_data['correct_answers']} из {len(user_data['selected_questions'])} вопросов.\nВведите /startquiz чтобы начать викторину или /startquiz_hardcore для режима хардкор.",
            reply_markup=ReplyKeyboardRemove()
        )

# Функция для обработки отправленных документов
async def handle_document(update: Update, context: CallbackContext):
    document = update.message.document
    if document and document.mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        file = await document.get_file()
        file_path = 'questions.docx'
        await file.download_to_drive(file_path)
        questions = read_questions_from_docx(file_path)
        context.user_data['questions'] = questions

        if questions:
            await update.message.reply_text("Вопросы загружены! Введите /startquiz чтобы начать викторину или /startquiz_hardcore для режима хардкор.Если нужно узнать список команд и инструкция но команда /help")
        else:
            await update.message.reply_text("Не удалось прочитать вопросы из документа. /help")
    else:
        await update.message.reply_text("Пожалуйста, отправьте документ в формате .docx. /help")

# Функция для предоставления инструкции
async def help_command(update: Update, context: CallbackContext):
    help_text = (
        "Привет! Я бот для проведения викторин.\n\n"
        "Вот список доступных команд:\n"
        "/start - Начать новую викторину.\n"
        "/startquiz - Начать обычную викторину с 50 вопросов.\n"
        "/startquiz_hardcore - Начать хардкорную викторину с полным списком вопросов от первого до последнего.\n"
        "/upload - Загрузить новый документ с вопросами.\n\n"
        "Чтобы загрузить вопросы, отправьте .docx файл с вопросами и ответами. "
        "Формат файла должен быть следующим:\n"
        "1. Вопрос на новой строке.\n"
        "2. Варианты ответов с префиксом 'A.', 'B.', 'C.', 'D.', 'E.'.\n"
        "3. Ответ на новой строке с префиксом 'ANSWER:'.\n\n"
        "Пример:\n"
        "Какого цвета небо?\n"
        "A. Синего\n"
        "B. Зеленого\n"
        "ANSWER: A\n\n"
        "Если у вас возникнут вопросы или проблемы, не стесняйтесь обращаться за помощью! @ladno_ok\n\n"
        "ВНИМАНИЕ!!! При обновлении бота будет сообщаться в группе в Whatsapp или Telegram, если бот уже обновился, нужно будет удалить весь старый диалог с ним."
    )
    await update.message.reply_text(help_text)

# Обновите основную функцию для добавления обработчика команды /upload
def main():
    application = Application.builder().token("YOR_BOT_TOKEN").build()

    application.add_handler(CommandHandler("start", start_quiz))
    application.add_handler(CommandHandler("startquiz", lambda update, context: start_quiz(update, context, hardcore=False)))
    application.add_handler(CommandHandler("startquiz_hardcore", lambda update, context: start_quiz(update, context, hardcore=True)))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("upload", handle_document))  # Добавляем обработчик команды /upload
    application.add_handler(MessageHandler(filters.Document.MimeType("application/vnd.openxmlformats-officedocument.wordprocessingml.document"), handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    application.run_polling()

if __name__ == "__main__":
    main()
