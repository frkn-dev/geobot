"""
This module provides a factory method that creates an instance of the bot.
"""
import requests
import telebot
from deta import Deta
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup


emojis = {
    "waving hand": "\U0001F44B",
    "magnifying glass": "\U0001F50D",
    "earth": "\U0001F30E",
    "thinking face": "\U0001F914",
    "diamond": "\U0001F539",
    "motorway": "\U0001F6E3",
    "postbox": "\U0001F4EE",
    "city": "\U0001F3D9",
}


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

        Sends welcome message.
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
                caption=f"{emojis['waving hand']} Hi, I will help you with `geocoding` - finding the coordinates of a place by name.",
            )

    @bot.message_handler(commands=["search"])
    def welcome_search(message: telebot.types.Message):
        """
        Handler for /search command.

        Sends a welcome message to search.
        """
        users.update({"state": "search"}, str(message.chat.id))
        bot.send_message(
            message.chat.id,
            f"{emojis['magnifying glass']} Send any name of the place to start the search.",
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
                bot.send_message(
                    message.chat.id,
                    f"{emojis['magnifying glass']} No results found.",
                )
            else:
                bot.delete_message(message.chat.id, message.message_id)
                bot.send_message(
                    message.chat.id,
                    f'{emojis["earth"]} I found these places by searching for "{message.text}":',
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    location["display_name"],
                                    callback_data=f"{location['lat']}:{location['lon']}",
                                )
                            ]
                            for location in locations
                        ]
                    ),
                )
        except Exception as exc:  # pylint: disable=W0703
            bot.send_message(
                message.chat.id,
                f"{emojis['thinking face']} Oops. Something went wrong.",
            )
            raise exc
        users.update({"state": None}, str(message.chat.id))

    @bot.callback_query_handler(func=lambda call: ":" in call.data)
    def show_location(callback: telebot.types.CallbackQuery):
        """
        Handler for inline keyboard buttons.

        Sends a location to the user.
        """
        latitude, longitude = 0, 0
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

        Sends a welcome message to advanced search.
        """
        users.update({"state": "advanced_search"}, str(message.chat.id))
        bot.send_message(
            message.chat.id,
            f"{emojis['diamond']} This is an advanced way to search place location. It is more accurate, but requires more precise data.\nChoose exactly what you know about the location you are looking for:",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"{emojis['earth']} Country",
                            callback_data="country",
                        ),
                        InlineKeyboardButton("State", callback_data="state"),
                        InlineKeyboardButton("County", callback_data="county"),
                    ],
                    [
                        InlineKeyboardButton(
                            f"{emojis['city']} City", callback_data="city"
                        ),
                        InlineKeyboardButton(
                            f"{emojis['motorway']} Street",
                            callback_data="street",
                        ),
                        InlineKeyboardButton(
                            f"{emojis['postbox']} Postal code",
                            callback_data="postal_code",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            f"{emojis['magnifying glass']} Search",
                            callback_data="search",
                        )
                    ],
                ]
            ),
        )

    @bot.callback_query_handler(
        func=lambda call: call.data
        in ["country", "state", "county", "city", "street", "postal_code"]
    )
    def add_details(callback: telebot.types.CallbackQuery):
        """
        Handler for inline keyboard buttons of advanced search menu.
        """
        markup = callback.message.reply_markup
        for row in markup.keyboard:
            for button in row:
                if button.callback_data == callback.data:
                    button.text = (
                        f"✔️ {button.text}"
                        if not button.text.startswith("✔️")
                        else button.text[1:]
                    )
        bot.edit_message_reply_markup(
            callback.message.chat.id,
            callback.message.message_id,
            reply_markup=markup,
        )

    return bot


__all__ = ["get_bot"]
