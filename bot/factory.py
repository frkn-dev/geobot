"""
This module provides a factory method that creates an instance of the bot.
"""
import requests
import telebot
from deta import Deta
from telebot.types import (
    ForceReply,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from . import messages


def get_locations(query: str = None, **details: dict) -> list:
    """
    Returns a list of locations from the nominantim API.
    """
    if details and query:
        raise ValueError("You can't use both query and details.")
    if not query and not details:
        raise ValueError("You must use either query or details.")
    if query:
        locations = requests.get(
            "https://nominatim.openstreetmap.org/search",
            {"q": query, "format": "json"},
        ).json()
    else:
        locations = requests.get(
            "https://nominatim.openstreetmap.org/search",
            {"format": "json", **details},
        ).json()
    return locations


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
                caption=messages.START_MESSAGE.substitute(),
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
            messages.SIMPLE_SEARCH_WELCOME_MESSAGE.substitute(),
            reply_markup=ForceReply(),
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
            messages.ADVANCED_SEARCH_WELCOME_MESSAGE.substitute(),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            f"\U0001F30E Country",
                            callback_data="country",
                        ),
                        InlineKeyboardButton("State", callback_data="state"),
                        InlineKeyboardButton("County", callback_data="county"),
                    ],
                    [
                        InlineKeyboardButton(
                            f"\U0001F3D9 City", callback_data="city"
                        ),
                        InlineKeyboardButton(
                            f"\U0001F6E3 Street",
                            callback_data="street",
                        ),
                        InlineKeyboardButton(
                            f"\U0001F4EE Postal code",
                            callback_data="postal code",
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            f"\U0001F50D Search",
                            callback_data="search",
                        )
                    ],
                ]
            ),
        )

    @bot.message_handler(
        func=lambda msg: users.get(str(msg.chat.id))["state"] == "search"
    )
    def search(message: telebot.types.Message):
        """
        A simple nominatim search for a given query text.
        """
        locations = get_locations(query=message.text)
        if len(locations) == 0:
            bot.send_message(
                message.chat.id,
                messages.NO_RESULTS_FOUND_MESSAGE.substitute(),
            )
        else:
            bot.send_message(
                message.chat.id,
                messages.SIMPLE_SEARCH_MESSAGE.substitute(query=message.text),
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

    @bot.callback_query_handler(func=lambda call: ":" in call.data)
    def show_location(callback: telebot.types.CallbackQuery):
        """
        Handler for inline keyboard buttons.

        Sends a location to the user.
        """
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

    @bot.callback_query_handler(
        func=lambda call: call.data
        in ["country", "state", "county", "city", "street", "postal code"]
    )
    def check_details(callback: telebot.types.CallbackQuery):
        """
        Handler for inline keyboard buttons(details) of advanced search menu.
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

    @bot.callback_query_handler(func=lambda call: call.data == "search")
    def add_details(callback: telebot.types.CallbackQuery):
        """
        Handler for search button of advanced search menu.
        """
        markup = callback.message.reply_markup
        details = [
            button.callback_data
            for row in markup.keyboard
            for button in row
            if button.text.startswith("✔️")
        ]
        if details:
            users.update(
                {
                    "details": details,
                },
                key=str(callback.message.chat.id),
            )
            if len(details) > 1:
                message_text = messages.WAIT_FOR_DETAILS_MESSAGE.substitute(
                    details=", ".join(details)
                )
            else:
                message_text = messages.WAIT_FOR_DETAIL_MESSAGE.substitute(
                    detail=details[0]
                )
            bot.edit_message_text(
                message_text,
                callback.message.chat.id,
                callback.message.message_id,
                reply_markup=ForceReply(),
            )
        else:
            bot.answer_callback_query(
                callback.id,
                messages.NEED_MORE_DETAILS_MESSAGE.substitute(),
            )

    @bot.message_handler(
        func=lambda msg: users.get(str(msg.chat.id))["state"]
        == "advanced_search"
    )
    def advanced_search(message: telebot.types.Message):
        details_types = users.get(str(message.chat.id))["details"]
        details = [detail.strip() for detail in message.text.split(",")]
        if len(details) != len(details_types):
            bot.send_message(
                message.chat.id,
                messages.INCORRECT_DETAILS_COUNT_MESSAGE.substitute(),
            )
        else:
            locations = get_locations(**dict(zip(details_types, details)))
            if len(locations) == 0:
                bot.send_message(
                    message.chat.id,
                    messages.NO_RESULTS_FOUND_MESSAGE.substitute(),
                    reply_to_message_id=message.message_id,
                )
            else:
                bot.send_message(
                    message.chat.id,
                    messages.ADVANCED_SEARCH_MESSAGE.substitute(),
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

    return bot


__all__ = ["get_bot"]
