"""
Webhooks handler for bot.
"""
from os import environ

import telebot
import flask
from bot import get_bot


app = flask.Flask(__name__)
bot = get_bot(
    environ.get("BOT_TOKEN"),
    environ.get("DETA_PROJECT_KEY"),
)
bot.set_webhook(environ.get("WEBHOOK_URL") + "/" + "webhook")


@app.route("/")
def index():
    """
    Display a small page about the bot with a link.
    """
    return flask.render_template("index.html")


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Handle webhooks.
    """
    try:
        data = flask.request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(data)
        bot.process_new_updates([update])
        return "ok"
    except Exception:  # pylint: disable=broad-except
        flask.abort(403)
    
