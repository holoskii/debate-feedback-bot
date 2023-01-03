#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

"""This example showcases how PTBs "arbitrary callback data" feature can be used.

For detailed info on arbitrary callback data, see the wiki page at
https://github.com/python-telegram-bot/python-telegram-bot/wiki/Arbitrary-callback_data
"""
import logging
from typing import List, Tuple, Dict, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    InvalidCallbackData,
    PicklePersistence, MessageHandler, Filters,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


rounds: List[str] = []
judges: List[str] = ['Judge 1', 'Judge 2']
confirmation: List[str] = ['Yes, confirm', 'No, cancel']

EVENT, ROUND, JUDGE, RATE, FINAL = range(5)


def start_command_handler(update: Update, context: CallbackContext) -> None:
    if len(rounds) > 1:
        update.message.reply_text('Choose round:', reply_markup=build_round_list({}))
    else:
        update.message.reply_text('Choose judge:', reply_markup=build_judge_list({}))


def help_command_handler(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "/start /help /clear"
    )


def clear_command_handler(update: Update, context: CallbackContext) -> None:
    context.bot.callback_data_cache.clear_callback_data()  # type: ignore[attr-defined]
    context.bot.callback_data_cache.clear_callback_queries()  # type: ignore[attr-defined]
    update.effective_message.reply_text('All clear!')


def build_round_list(current_list: Dict[int, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton(str(round), callback_data=(round, current_list, ROUND)) for round in rounds]
    )


def build_judge_list(current_list: Dict[int, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton(str(judge), callback_data=(judge, current_list, JUDGE)) for judge in judges]
    )


def build_rate_list(current_list: Dict[int, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton(str(i), callback_data=(i, current_list, RATE)) for i in range(1, 6)]
    )


def build_confirmation_list(current_list: Dict[int, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton(str(option), callback_data=(option, current_list, FINAL)) for option in confirmation]
    )


def list_button_handler(update: Update, context: CallbackContext) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    query.answer()
    # Get the data from the callback_data.
    # If you're using a type checker like MyPy, you'll have to use typing.cast
    # to make the checker get the expected type of the callback_data
    string, string_dict, phase = cast(Tuple[str, Dict[int, str], int], query.data)
    # append the number to the list
    string_dict[phase] = string

    # EVENT, ROUND, JUDGE, RATE
    if phase == EVENT:
        query.edit_message_text(
            text=f"Selections: {string_dict}. Choose round",
            reply_markup=build_round_list(string_dict),
        )
    elif phase == ROUND:
        query.edit_message_text(
            text=f"Selections: {string_dict}. Choose round",
            reply_markup=build_round_list(string_dict),
        )
    elif phase == JUDGE:
        query.edit_message_text(
            text=f"Selections: {string_dict}. Choose Judge",
            reply_markup=build_rate_list(string_dict),
        )
    elif phase == RATE:
        query.edit_message_text(
            text=f"Selections: {string_dict}. Are you sure?",
            reply_markup=build_confirmation_list(string_dict),
        )
    elif phase == FINAL:
        if string_dict[FINAL] == 'Yes, confirm':
            query.edit_message_text(text=f"Selections: {string_dict}. Done and saved")
        elif string_dict[FINAL] == 'No, cancel':
            query.edit_message_text(text=f"Answer discarded")
        else:
            print('Uncaught branch')

    # we can delete the data stored for the query, because we've replaced the buttons
    context.drop_callback_data(query)


def invalid_button_handler(update: Update, context: CallbackContext) -> None:
    update.callback_query.answer()
    update.effective_message.edit_text('This button is already invalid. Use /start')


def unknown_command_handler(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="This command is not supported. Use /start")


def text_handler(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Text is not supported. Use /start")


def main() -> None:
    """Run the bot."""
    # We use persistence to demonstrate how buttons can still work after the bot was restarted
    persistence = PicklePersistence(
        filename='arbitrarycallbackdatabot.pickle', store_callback_data=True
    )
    # Create the Updater and pass it your bot's token.
    updater = Updater("TOKEN", persistence=persistence, arbitrary_callback_data=True)

    updater.dispatcher.add_handler(CommandHandler('start', start_command_handler))
    updater.dispatcher.add_handler(CommandHandler('help', help_command_handler))
    updater.dispatcher.add_handler(CommandHandler('clear', clear_command_handler))
    updater.dispatcher.add_handler(CallbackQueryHandler(invalid_button_handler, pattern=InvalidCallbackData))
    updater.dispatcher.add_handler(CallbackQueryHandler(list_button_handler))
    updater.dispatcher.add_handler(MessageHandler(Filters.command, unknown_command_handler))
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, text_handler))

    # Start the Bot
    updater.start_polling()

    # Run the bot until the user presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT
    updater.idle()


if __name__ == '__main__':
    main()
