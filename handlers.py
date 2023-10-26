from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from database.models import db, User, ReferralLink, Question, Answer
import logging
import uuid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_referral_link(user):
    unique_code = uuid.uuid4().hex  # Создаем уникальный код
    referral_link = ReferralLink(
        user_id=user.id,
        link=f'https://t.me/sendmequestion_bot?start={unique_code}'
    )
    db.session.add(referral_link)
    db.session.commit()

    return referral_link.link

def show_keyboard(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Задать вопрос", callback_data='ask')],
        [InlineKeyboardButton("Посмотреть историю ответов", callback_data='history')],
        [InlineKeyboardButton("Задать мне вопрос", callback_data='create_referral')]
        # Добавьте другие кнопки по мере необходимости
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Выберите действие:', reply_markup=reply_markup)

def handle_callback(update: Update, context: CallbackContext):
    logger.info('handle_callback called')
    query = update.callback_query
    query.answer()  # Ответить на запрос обратного вызова, чтобы убрать индикатор загрузки

    user_id = update.effective_user.id
    user = User.query.filter_by(telegram_id=user_id).first()

    query_data = query.data.split('_')
    action = query_data[0]
    if len(query_data) > 1:
        item_id_str = query_data[1]
        if item_id_str.isnumeric():
            item_id = int(item_id_str)
        else:
            item_id = None
    else:
        item_id = None

    if action == 'answer' and item_id:
        # Сохраняем question_id в данных пользователя, чтобы затем использовать его при получении ответа
        context.user_data['question_id'] = item_id
        query.message.reply_text('Пожалуйста, введите свой ответ на вопрос:')
    elif action == 'ask':
        query.message.reply_text('Пожалуйста, введите свой вопрос:')
        # Добавьте свой код для обработки запроса здесь
    elif query.data == 'history':
        # Получаем последние 10 вопросов и ответов пользователя
        recent_questions = (
            Question.query.join(ReferralLink, ReferralLink.id == Question.referral_link_id)
            .join(User, User.id == ReferralLink.user_id)
            .filter(User.id == user.id)
            .order_by(Question.id.desc())
            .limit(10)
            .all()
        )

        history_text = ''
        for question in recent_questions:
            answer = Answer.query.filter_by(question_id=question.id).first()
            if answer:
                history_text += f'Вопрос: {question.text}\nОтвет: {answer.text}\n\n'

        if history_text:
            query.message.reply_text(history_text)
        else:
            query.message.reply_text('У вас нет истории ответов.')
    elif query.data == 'create_referral':
        # Создание уникальной реферальной ссылки
        referral_link = create_referral_link(user)
        query.message.reply_text(f'Ваша реферальная ссылка: {referral_link}')

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = User.query.filter_by(telegram_id=user_id).first()
    if not user:
        user = User(telegram_id=user_id)
        db.session.add(user)
        db.session.commit()
    
    referral_code = context.args[0] if context.args else None

    if referral_code:
        referral_link = ReferralLink.query.filter_by(link=f'https://t.me/sendmequestion_bot?start={referral_code}').first()
        if referral_link:
            context.user_data['referral_link_id'] = referral_link.id
            update.message.reply_text('Напишите вопрос пользователю ниже:')
        else:
            update.message.reply_text('Неверная реферальная ссылка. Пожалуйста, начните заново.')
    else:
        show_keyboard(update, context)
        
def help_command(update: Update, context: CallbackContext):
    update.message.reply_text('Это команда помощи. Напиши /ask, чтобы задать вопрос.')

def text_message(update: Update, context: CallbackContext):
    logger.info(f'text_message called with text: {update.message.text}')

    referral_link_id = context.user_data.get('referral_link_id')
    question_id = context.user_data.get('question_id')
    
    user_id = update.effective_user.id  # Получаем ID пользователя, который задал вопрос
    user = User.query.filter_by(telegram_id=user_id).first()

    if user is None:
        # Если пользователь не существует, создаем нового пользователя
        user = User(telegram_id=user_id)
        db.session.add(user)
        db.session.commit()
    
    if referral_link_id:        
        logger.info(f'Processing question from referral link ID: {referral_link_id}')  # Добавлено логирование

        # Обработка отправки вопроса
        question_text = update.message.text
        question = Question(referral_link_id=referral_link_id, asker_id=user.id, text=question_text)  # Используем user.id вместо user_id
        db.session.add(question)
        db.session.commit()
        
        # Отправляем пользователю сообщение, что его вопрос был отправлен
        update.message.reply_text('Ваш вопрос отправлен')
        
        referral_link = ReferralLink.query.get(referral_link_id)
        referrer = User.query.get(referral_link.user_id)
        
        # Создание кнопки для ответа
        keyboard = [[InlineKeyboardButton("Ответить на вопрос", callback_data=f'answer_{question.id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Теперь отправьте вопрос пользователю, который создал реферальную ссылку
        context.bot.sendMessage(
            chat_id=referrer.telegram_id, 
            text=f'Вам задали вопрос: {question_text}',
            reply_markup=reply_markup
        )
    else:
        if question_id:
            logger.info(f'Processing answer for question ID: {question_id}')  # Добавлено логирование

            answer_text = update.message.text
            answer = Answer(question_id=question_id, text=answer_text)
            db.session.add(answer)
            db.session.commit()

            question = Question.query.get(question_id)
            referral_link = ReferralLink.query.get(question.referral_link_id)
            asker = User.query.get(question.asker_id)  # Измените эту строку


                        # Уведомляем пользователя об ответе
            logger.info(f'Sending answer to user with Telegram ID: {asker.telegram_id}')
            # Создание кнопки для ответа
            keyboard = [[InlineKeyboardButton("Ответить", callback_data=f'reply_{question.id}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Отправка сообщения с кнопкой
            context.bot.sendMessage(
                chat_id=asker.telegram_id, 
                text=f'На ваш вопрос: "{question.text}" получен ответ: {answer_text}',
                reply_markup=reply_markup
            )
            logger.info(f'Answer sent to user with Telegram ID: {asker.telegram_id}')

            # Отправляем уведомление пользователю, который ответил на вопрос
            update.message.reply_text('Ответ на вопрос отправлен.')

            # Очищаем question_id из данных пользователя
            context.user_data.pop('question_id', None)
        else:
            update.message.reply_text('Пожалуйста, используй команды для взаимодействия с ботом.')

handlers = [
    CommandHandler("start", start),
    CommandHandler("help", help_command),
    MessageHandler(Filters.text & ~Filters.command, text_message),
    CallbackQueryHandler(handle_callback),  # Добавьте эту строку
]
