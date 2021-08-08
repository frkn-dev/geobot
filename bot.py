"""
This module provides a factory method that creates an instance of the bot.
"""
import requests
import telebot
from deta import Deta
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_bot(bot_token: str, deta_project_key: str) -> telebot.AsyncTeleBot:
    """
    Creates an instance of the bot.

    Args:
        bot_token: The bot's token.
        deta_project_key: The deta project key.

    Returns:
        telebot.AsyncTeleBot: bot instance.
    """
    deta = Deta(deta_project_key)
    users = deta.Base("users")
    bot = telebot.TeleBot(bot_token, parse_mode="Markdown")

    @bot.message_handler(commands=["start"])
    def start(message: telebot.types.Message):
        """
        Handler for /start command.

        Send welcome message.
        Adds the user to the database or sets the default state.
        """
        try:
            users.insert({"state": None}, str(message.chat.id))
        except Exception:  # pylint: disable=W0703
            users.update({"state": None}, str(message.chat.id))
        with open("static/cover.png", "rb") as cover:
            bot.send_photo(
                message.chat.id,
                photo=cover,
                caption="👋 Hi, i will help you with `geocoding` - finding the coordinates of a place by name.",
            )

    @bot.message_handler(commands=["search"])
    def welcome_search(message: telebot.types.Message):
        """
        Handler for /search command.

        Send a welcome message to search.
        """
        users.update({"state": "search"}, str(message.chat.id))
        bot.send_message(
            message.chat.id,
            "🔍 Send any name of the place to start the search.",
        )

    @bot.message_handler(
        func=lambda msg: users.get(str(msg.chat.id))["state"] == "search"
    )
    def search(message: telebot.types.Message):
        """
        A simple nominatim search for a given query text.
        """
        try:
            locations = requests.get(
                "https://nominatim.openstreetmap.org/search",
                {"q": message.text, "format": "json"},
            ).json()
            if len(locations) == 0:
                bot.send_message(message.chat.id, "🔍 No results found.")
            else:
                bot.delete_message(message.chat.id, message.message_id)
                bot.send_message(
                    message.chat.id,
                    '🌎 I found these places by searching for "{}":'.format(
                        message.text
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    location["display_name"],
                                    callback_data="{}:{}".format(
                                        location["lat"], location["lon"]
                                    ),
                                )
                            ]
                            for location in locations
                        ]
                    ),
                )
        except Exception as exc:  # pylint: disable=W0703
            bot.send_message(message.chat.id, "🤔 Oops. Something went wrong.")
            raise exc
        users.update({"state": None}, str(message.chat.id))

    @bot.callback_query_handler(func=lambda call: ":" in call.data)
    def show_location(callback: telebot.types.CallbackQuery):
        """
        Handler for inline keyboard buttons.

        Sends a location to the user.
        """
        if ":" in callback.data:
            latitude, longitude = callback.data.split(":")
        bot.delete_message(
            callback.message.chat.id, callback.message.message_id
        )
        bot.send_location(
            callback.message.chat.id,
            latitude,
            longitude,
            reply_markup=callback.message.reply_markup,
        )
    @bot.message_handler(commands=["advanced"])
    def welcome_advanced_search(message: telebot.types.Message):
        """
        Handler for /advanced command.

        Send a welcome message to advanced search.
        """
        users.update({"state": "advanced_search"}, str(message.chat.id))
        bot.send_message(
            message.chat.id,
            "🔹 This is an advancde way to search place location. It is more accurate, but requires more precise data.\nChoose exactly what you know about the location you are looking for:",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🌎 Country", callback_data="country"
                        ),
                        InlineKeyboardButton("State", callback_data="state"),
                        InlineKeyboardButton("County", callback_data="county"),
                    ],
                    [
                        InlineKeyboardButton("🏙️ City", callback_data="city"),
                        InlineKeyboardButton(
                            "🛣️ Street", callback_data="street"
                        ),
                        InlineKeyboardButton(
                            "📮 Postal code", callback_data="postal_code"
                        ),
                    ],
                    [InlineKeyboardButton("🔍 Search", callback_data="search")],
                ]
            ),
        )

    return bot


__all__ = ["get_bot"]
