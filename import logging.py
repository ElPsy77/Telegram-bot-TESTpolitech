import logging
import random
import docx
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Включение логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Функция для чтения вопросов из .docx файла
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
                questions.append({
                    "question": question_text.strip(),
                    "options": options,
                    "answer": correct_answer
                })
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

    return questions

# Функция для старта викторины
async def start_quiz(update: Update, context: CallbackContext):
    user_data = context.user_data
    if 'questions' not in user_data or not user_data['questions']:
        await update.message.reply_text("Вопросы не найдены. Пожалуйста, отправьте документ с вопросами.")
        return

    questions = user_data['questions']
    num_questions = min(len(questions), 50)
    random.shuffle(questions)
    user_data['selected_questions'] = questions[:num_questions]
    user_data['current_question'] = 0
    user_data['correct_answers'] = 0

    await ask_question(update, context)

# Функция для задавания вопросов
async def ask_question(update: Update, context: CallbackContext):
    user_data = context.user_data
    current_question = user_data['current_question']
    question = user_data['selected_questions'][current_question]

    options_text = "\n".join([f"{opt}. {txt}" for opt, txt in question['options'].items()])
    await update.message.reply_text(f"Вопрос {current_question + 1}:\n{question['question']}\n\nВарианты ответов:\n{options_text}\n\nВаш ответ (укажите букву варианта ответа):")

# Функция для обработки ответов
async def handle_answer(update: Update, context: CallbackContext):
    user_data = context.user_data
    user_answer = update.message.text.strip().upper()
    current_question = user_data['current_question']
    question = user_data['selected_questions'][current_question]

    if user_answer == question['answer']:
        await update.message.reply_text("Верно!")
        user_data['correct_answers'] += 1
    else:
        await update.message.reply_text(f"Неверно. Правильный ответ: {question['answer']}")

    user_data['current_question'] += 1
    if user_data['current_question'] < len(user_data['selected_questions']):
        await ask_question(update, context)
    else:
        await update.message.reply_text(f"Викторина завершена! Вы ответили правильно на {user_data['correct_answers']} из {len(user_data['selected_questions'])} вопросов.")

# Функция для обработки отправленных документов
async def handle_document(update: Update, context: CallbackContext):
    file = await update.message.document.get_file()
    file_path = 'questions.docx'
    await file.download_to_drive(file_path)
    questions = read_questions_from_docx(file_path)
    context.user_data['questions'] = questions

    if questions:
        await update.message.reply_text("Вопросы загружены! Введите /startquiz чтобы начать викторину.")
    else:
        await update.message.reply_text("Не удалось прочитать вопросы из документа.")

# Основная функция для старта бота
def main():
    application = Application.builder().token("7303376727:AAH1cFsAFAixv7X8zF9mkLtuijap4EiL5jM").build()

    application.add_handler(CommandHandler("start", start_quiz))
    application.add_handler(CommandHandler("startquiz", start_quiz))
    application.add_handler(MessageHandler(filters.Document.MimeType("application/vnd.openxmlformats-officedocument.wordprocessingml.document"), handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    application.run_polling()

if __name__ == "__main__":
    main()
