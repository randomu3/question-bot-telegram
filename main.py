from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters
from database.models import db
from handlers import handlers  # Импорт обработчиков
import config

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

bot = Bot(token=config.TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

for handler in handlers:  # Регистрация обработчиков
    dispatcher.add_handler(handler)

def echo(update: Update, context):
    update.message.reply_text(update.message.text)

dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
