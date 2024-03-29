"""
This module provides a factory method that creates an instance of the bot.
"""
from typing import List, Tuple
from pprint import pprint as print
import zlib
import requests
import telebot
from deta import Deta
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
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


def location_name(lat: float, lon: float) -> str:
    """
    Returns the name of the location from the nominantim API.
    """
    return requests.get(
        "https://nominatim.openstreetmap.org/reverse",
        {"lat": lat, "lon": lon, "format": "json"},
    ).json()["display_name"]


def paginate_locations(
    locations: List[Tuple[str, Tuple[float, float]]]
) -> InlineKeyboardMarkup:
    """
    Returns a paginated inline keyboard with the given locations.

    The locations are paginated in groups of 2.
    Inline keyboard is splitted on two parts:
        1. First part contains the first three locations.
        2. Pages.
    """
    first = [
        [
            InlineKeyboardButton(
                location[0],
                callback_data=f"{location[1][0]}:{location[1][1]}",
            )
        ]
        for location in locations[:2]
    ]
    if len(locations) > 2:
        second = [
            [
                InlineKeyboardButton(
                    index + 1,
                    callback_data="/".join(
                        ":".join(location[1]) for location in page
                    ),
                )
                for index, page in enumerate(
                    tuple(locations[i : i + 2])
                    for i in range(0, len(locations), 2)
                )
            ]
        ]
    else:
        second = []
    return InlineKeyboardMarkup(first + second, row_width=5)


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

    @bot.message_handler(commands=["help"])
    def help(message: telebot.types.Message):
        """
        Sends a help message.
        """
        bot.send_message(
            message.chat.id,
            messages.HELP_MESSAGE.substitute(),
        )

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
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        keyboard.add(
            KeyboardButton("Basic search"),
            KeyboardButton("Advanced search"),
        )
        bot.send_message(
            message.chat.id,
            messages.START_MESSAGE.substitute(),
            reply_markup=keyboard,
        )

    @bot.message_handler(regexp=r"^(/search)|(Basic search)$")
    def welcome_search(message: telebot.types.Message):
        """
        Handler for /search command.

        Sends a welcome message to search.
        """
        users.update({"state": "search"}, str(message.chat.id))
        bot.send_message(
            message.chat.id,
            messages.SIMPLE_SEARCH_WELCOME_MESSAGE.substitute(),
        )

    @bot.message_handler(regexp=r"^(\/advanced)|(Advanced search)$")
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
                reply_markup=paginate_locations(
                    [
                        (
                            location["display_name"],
                            (location["lat"], location["lon"]),
                        )
                        for location in locations
                    ]
                ),
            )

    @bot.callback_query_handler(
        func=lambda call: len(call.data.split(":")) == 2
    )
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

    @bot.callback_query_handler(func=lambda call: "/" in call.data)
    def switch_page(callback: telebot.types.CallbackQuery):
        """
        Handler for pagination buttons.
        """
        pages = [callback.message.reply_markup.keyboard[2]]
        locations = []
        for coord in callback.data.split("/"):
            lat, lon = coord.split(":")
            locations.append(
                [
                    InlineKeyboardButton(
                        location_name(lat, lon),
                        callback_data=f"{lat}:{lon}",
                    )
                ]
            )
        try:
            bot.edit_message_reply_markup(
                callback.message.chat.id,
                callback.message.message_id,
                callback.inline_message_id,
                reply_markup=InlineKeyboardMarkup(locations + pages),
            )
        except Exception:
            bot.answer_callback_query(
                callback.id, messages.CHANGE_CURRENT_PAGE_ERROR.substitute()
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
                    reply_markup=paginate_locations(
                        [
                            (
                                location["display_name"],
                                (location["lat"], location["lon"]),
                            )
                            for location in locations
                        ]
                    ),
                )

    return bot


__all__ = ["get_bot"]
