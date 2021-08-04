"""
Webhooks handler for bot.
"""
import flask


app = flask.Flask(__name__)


@app.route("/")
def index():
    """
    Display a small page about the bot with a link.
    """
    return flask.render_template("index.html")
