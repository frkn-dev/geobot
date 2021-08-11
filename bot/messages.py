from string import Template


START_MESSAGE = Template(
    "\U0001F44B Hi, I will help you with `geocoding` - finding the coordinates of a place by name."
)
SIMPLE_SEARCH_WELCOME_MESSAGE = Template(
    "\U0001F50D Send any name of the place to start the search.",
)
ADVANCED_SEARCH_WELCOME_MESSAGE = Template(
    "\U0001F539 This is an *advanced way to search place location.* It is more accurate, but requires more precise data.\n\u2611\ufe0f Choose exactly what you know about the location you are looking for:"
)
NO_RESULTS_FOUND_MESSAGE = Template("\U0001F50D No results found.")
SIMPLE_SEARCH_MESSAGE = Template(
    '\U0001F30E I found these places by searching for "$query":'
)
ADVANCED_SEARCH_MESSAGE = Template("\U0001F30E I found these places:")
WAIT_FOR_DETAILS_MESSAGE = Template(
    "Ok. Send me $details names separated by comma."
)
WAIT_FOR_DETAIL_MESSAGE = Template("Ok. Send me $detail name.")
NEED_MORE_DETAILS_MESSAGE = Template(
    "You need to know at least one of the details of the place."
)
INCORRECT_DETAILS_COUNT_MESSAGE = Template(
    "You need to send all details for each place."
)


__all__ = [
    "START_MESSAGE",
    "SIMPLE_SEARCH_WELCOME_MESSAGE",
    "ADVANCED_SEARCH_WELCOME_MESSAGE",
    "NO_RESULTS_FOUND_MESSAGE",
    "SIMPLE_SEARCH_MESSAGE",
    "ADVANCED_SEARCH_MESSAGE",
    "WAIT_FOR_DETAILS_MESSAGE",
    "WAIT_FOR_DETAIL_MESSAGE",
    "NEED_MORE_DETAILS_MESSAGE",
    "INCORRECT_DETAILS_COUNT_MESSAGE",
]
