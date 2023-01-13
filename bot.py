#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
"""
Install:
pip install python-telegram-bot --upgrade
pip install python-telegram-bot[callback-data]
"""

import logging
from typing import List, Tuple, Dict, cast
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes, InvalidCallbackData, PicklePersistence, MessageHandler, filters)

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN_STR: str = "5619034469:AAEqO4pvEyMar53o3ZIlPj2aYWpDPUNehy4"
ROUND, JUDGE, RATE1, FEEDBACK, CONFIRMATION = range(1, 6)
rounds: List[str] = ["Round 1", "Round 2", "Round 3", "Final"]
judges: List[str] = ["Judge 1", "Judge 2", "Judge 3"]
max_rate: int = 5


# Turn user answers into human-readable format
def answers_to_str(m_dict: Dict[int, str]) -> str:
    result: str = ""
    if ROUND in m_dict:
        result += f"Round: {m_dict[ROUND]}\n"
    if JUDGE in m_dict:
        result += f"Judge: {m_dict[JUDGE]}\n"
    if RATE1 in m_dict:
        result += f"Judge rate: {m_dict[RATE1]}\n"
    if FEEDBACK in m_dict:
        result += f"Feedback: {m_dict[FEEDBACK]}\n"
    return result


# Here all UI text is generated (except for /start command)
def get_text_and_reply_markup(stage: int, answers: Dict[int, str]) -> (str, InlineKeyboardMarkup):
    text: str = ""
    buttons: List[Tuple[str, Dict[int, str], int]] = []
    if stage == ROUND:
        text = "Choose round:"
        for round in rounds:
            buttons.append((round, answers, stage))
    elif stage == JUDGE:
        text = "Choose judge name:"
        for judge in judges:
            buttons.append((judge, answers, stage))
    elif stage == RATE1:
        text = "How would you rate the judge?"
        for rate in range(1, max_rate + 1):
            buttons.append((str(rate), answers, stage))
    elif stage == FEEDBACK:
        text = "Input your feedback as a text (or press No feedback button)"
        buttons.append((str("No feedback"), answers, stage))
    elif stage == CONFIRMATION:
        text = "Is everything correct?"
        for m_str in ["YES", "NO"]:
            buttons.append((m_str, answers, stage))

    reply_markup = InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton(button[0], callback_data=button) for button in buttons]
    )

    text_markup = f"Your selection so far:\n{answers_to_str(answers)}\n{text}"
    return text_markup, reply_markup


async def button_press_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    # Save the answer
    m_str, m_dict, m_stage = cast(Tuple[str, Dict[int, str], int], query.data)
    m_dict[m_stage] = m_str

    if m_stage != CONFIRMATION:
        # Progress Stage
        text, reply_markup = get_text_and_reply_markup(m_stage + 1, m_dict)
        context.user_data["key"] = (m_dict, m_stage + 1)
    else:
        # The last answer handling
        reply_markup = InlineKeyboardMarkup.from_column([])
        if m_dict[CONFIRMATION] == "YES":
            # Save answer here
            text = f"Your selections\n{answers_to_str(m_dict)}\nAnswers are saved"
        else:
            text = f"Results discarded. Use /start to fill new form"

    await query.edit_message_text(text=text, reply_markup=reply_markup)
    context.drop_callback_data(query)


def setup_callbacks(application: Application) -> None:
    async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        m_dict: Dict[int, str] = {}
        text_markup, reply_markup = get_text_and_reply_markup(ROUND, m_dict)
        await update.message.reply_text("Choose round:", reply_markup=reply_markup)

    async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("New feedback form: /start")

    async def clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.bot.callback_data_cache.clear_callback_data()
        context.bot.callback_data_cache.clear_callback_queries()
        await update.effective_message.reply_text("callback_data_cache cleared")

    async def unknown_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Unknown command. Use /start to start new feedback form")

    async def invalid_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.callback_query.answer()
        await update.effective_message.edit_text("Invalid button. If you want to submit new feedback form use /start")

    async def text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        m_dict, m_stage = context.user_data["key"]
        if m_stage != FEEDBACK:
            await update.message.reply_text("Text is not accepted at the moment. "
                                            "Finish feedback form or start new feedback form with /start")
        else:
            m_dict[FEEDBACK] = update.message.text
            context.user_data["key"] = (m_dict, m_stage)
            text, reply_markup = get_text_and_reply_markup(CONFIRMATION, m_dict)
            await update.message.reply_text(text, reply_markup=reply_markup)

    application.add_handler(CommandHandler("start", start_callback))
    application.add_handler(CommandHandler("help", help_callback))
    application.add_handler(CommandHandler("clear", clear_callback))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command_callback))
    application.add_handler(CallbackQueryHandler(invalid_button_callback, pattern=InvalidCallbackData))
    application.add_handler(CallbackQueryHandler(button_press_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_callback))


def check_version() -> None:
    from telegram import __version__ as TG_VER

    try:
        from telegram import __version_info__
    except ImportError:
        __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

    if __version_info__ < (20, 0, 0, "alpha", 1):
        raise RuntimeError(
            f"This example is not compatible with your current PTB version {TG_VER}. To view the "
            f"{TG_VER} version of this example, "
            f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
        )


def main() -> None:
    check_version()

    application = (
        Application.builder()
        .token(TOKEN_STR)
        .persistence(PicklePersistence(filepath="debate_test_bot.picklepersistence"))
        .arbitrary_callback_data(True)
        .build()
    )

    setup_callbacks(application)
    application.run_polling()


if __name__ == "__main__":
    main()