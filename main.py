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
bot.set_webhook(environ.get("WEBHOOK_URL") + "/" + environ.get("BOT_TOKEN"))


@app.route("/")
def index():
    """
    Display a small page about the bot with a link.
    """
    return flask.render_template("index.html")


@app.route("/<token>", methods=["POST"])
def webhook(token: str):
    """
    Handle webhooks.
    """
    data = flask.request.get_json(silent=True, force=True)
    if data:
        try:
            update = telebot.types.Update.de_json(data)
            bot.process_new_updates([update])
        except Exception:  # pylint: disable=broad-except
            ...
    return "ok"
