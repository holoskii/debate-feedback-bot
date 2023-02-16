#!/usr/bin/env python
# pylint: disable=unused-argument, wrong-import-position
"""
Install:
pip install python-telegram-bot --upgrade
pip install python-telegram-bot[callback-data]
"""
import asyncio
from datetime import datetime

import logging
from typing import List, Tuple, Dict, cast

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Chat
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes, InvalidCallbackData,
                          PicklePersistence, MessageHandler, filters, ApplicationBuilder)

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

###############################################################
# SETTINGS

# If this string is empty no message will be sent and bot will start in normal mode
# Otherwise, the message will be sent to all users and BOT WILL NOT BE STARTED
message_to_all_users: str = ''

output_filename = 'answers_out.csv'
chat_ids_filename = 'chat_ids.txt'

TOKEN_STR: str = "TOKEN"

ROUND, JUDGE, TEAM, PLACE, RATE1, RATE2, RATE3, RATE4, FEEDBACK, CONFIRMATION = range(1, 11)
choices_dict: Dict[int, List[str]] = {
    ROUND: ["1", "2", "3", "Полуфинал", "Финал"],
    JUDGE: ["Настя", "Владислав", "Илья"],
    TEAM: ["Team 1", "Team 2", "Team 3", "Team 4", "Team 5"],
    PLACE: ["1 место", "2 место", "3 место", "4 место"],
    RATE1: ["1", "2", "3", "4", "5"],
    RATE2: ["1", "2", "3", "4", "5"],
    RATE3: ["1", "2", "3", "4"],
    RATE4: ["Соблюдено", "Не соблюдено"],
    FEEDBACK: ["Нет отзыва"],
    CONFIRMATION: ["ДА", "НЕТ"],
}

question_dict: Dict[int, str] = {
    ROUND: "Выбери раунд:",
    JUDGE: "Выбери судью:",
    TEAM:  "Выбери свою команду:",
    PLACE: "Какое место занял в раунде:",
    RATE1: "Анализ речей судьей\n1 - Очень непонятный, странный анализ\n5 - Все понятно, вряд ли можно сделать лучше",
    RATE2: "Насколько качественно проведено сравнение комманд?\n1 - Очень непонятные, странные критерии\n5 - Все понятно, сомнений в местах нет",
    RATE3: "Насколько фидбек полезен для дальнейшего развития\n1 - Не было предложений по улучшению\n4 - Ясно как выиграть раунд или повысить качество речей",
    RATE4: "Оцени ведение раунда, соблюдался ли регламент, был ли соблюдён порядок",
    FEEDBACK: "Комментарий для главного судьи, не обязательно (Отправь текстовое сообщение с отзывом, или нажми \"Нет отзыва\")",
    CONFIRMATION: "Всё правильно?",
}

summary_dict: Dict[int, str] = {
    ROUND: "Раунд:",
    JUDGE: "Судья:",
    TEAM:  "Команда:",
    PLACE: "Место:",
    RATE1: "Анализ речей судьей:",
    RATE2: "Сравнение команд:",
    RATE3: "Полезность:",
    RATE4: "Ведение раунда:",
    FEEDBACK: "Комментарии:",
}

# END SETTINGS
###############################################################


# save the answer
def save_answers(m_dict: Dict[int, str], chat: telegram.Chat) -> None:
    current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result: str = f"{current_datetime},{chat.id},{chat.username},{chat.full_name},"

    for answer in m_dict:
        value = m_dict[answer]
        if answer == FEEDBACK:
            if m_dict[FEEDBACK] == "Нет отзыва":
                value = ''
        result += f"{value},"
    result = result[:-1]
    result += "\n"

    print("Completed feedback: " + result, end='')
    # Open the file in append & read mode ('a+')
    myfile = open(output_filename, "a")
    myfile.write(result)


# Turn user answers into human-readable format
def answers_to_str(m_dict: Dict[int, str]) -> str:
    result: str = ""
    for answer in m_dict:
        if answer == CONFIRMATION:
            continue
        if answer == FEEDBACK:
            if m_dict[FEEDBACK] == "Нет отзыва":
                continue

        if answer in summary_dict:
            result += f"{summary_dict[answer]} {m_dict[answer]}\n"
        else:
            print("Not in summary_dict: " + str(answer))
    return result


# Here all UI text is generated (except for /start command)
def get_text_and_reply_markup(stage: int, answers: Dict[int, str]) -> (str, InlineKeyboardMarkup):
    text: str = ""
    buttons: List[Tuple[str, Dict[int, str], int]] = []
    if (stage in choices_dict) and (stage in question_dict):
        text = question_dict[stage]
        for options in choices_dict[stage]:
            buttons.append((options, answers, stage))
    else:
        print("Unhandled branch, stage=" + str(stage))

    reply_markup = InlineKeyboardMarkup.from_column(
        [InlineKeyboardButton(button[0], callback_data=button) for button in buttons]
    )

    text_markup = f"Твой выбор:\n{answers_to_str(answers)}\n{text}"
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
        if m_dict[CONFIRMATION] == "ДА":
            # Save answer here
            text = f"Твой отзыв\n{answers_to_str(m_dict)}\nОтвет сохранён"
            save_answers(m_dict, update.effective_chat)
        else:
            text = f"Ответ не был сохранён. Используй /start чтобы начать заново"

    await query.edit_message_text(text=text, reply_markup=reply_markup)
    context.drop_callback_data(query)


def try_add_chat_id_to_file(chat_id_int: int) -> None:
    chat_id: str = str(chat_id_int)
    print('Trying to add chat id to file = ' + str(chat_id) + ' ...')
    with open('chat_ids.txt') as file:
        for line in file:
            if line == (chat_id + '\n'):
                print('... already present in file')
                return
        file.close()
    print('... added')

    file_object = open('chat_ids.txt', 'a')
    file_object.write(chat_id + '\n')
    file_object.close()


def setup_callbacks(application: Application) -> None:
    async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chat = update.effective_chat
        result: str = f"{current_datetime},{chat.id},{chat.username},{chat.full_name}"
        print(f"New start command: {result}")
        m_dict: Dict[int, str] = {}
        try_add_chat_id_to_file(chat.id)
        if len(choices_dict[ROUND]) != 0:
            text_markup, reply_markup = get_text_and_reply_markup(ROUND, m_dict)
            text_markup = "Выбери раунд:"
        else:
            text_markup, reply_markup = get_text_and_reply_markup(JUDGE, m_dict)
            text_markup = "Выбери судью:"
        await update.message.reply_text(text_markup, reply_markup=reply_markup)

    async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Начать новую форму: /start")

    async def clear_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        context.bot.callback_data_cache.clear_callback_data()
        context.bot.callback_data_cache.clear_callback_queries()
        await update.effective_message.reply_text("callback_data_cache cleared")

    async def unknown_command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Неизвестная команда, используй /start чтобы заполнить новую форму")

    async def invalid_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.callback_query.answer()
        await update.effective_message.edit_text("Нерабочая кнопка. Чтобы начать новую форму используй /start")

    async def text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        m_dict, m_stage = context.user_data["key"]
        if m_stage != FEEDBACK:
            await update.message.reply_text("Сейчас текст не принимается. "
                                            "Продолжай заолнять форму, или начни новую с помощью /start")
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


def try_send_message_to_all_users() -> bool:
    if len(message_to_all_users) == 0:
        return False

    async def send_and_wait(bot_token: str, chat_id: int, text: str):
        application = ApplicationBuilder().token(bot_token).build()
        await application.bot.sendMessage(chat_id=chat_id, text=text)
    num_lines: int = 0
    with open('chat_ids.txt') as file:
        for line in file:
            num_lines += 1
        file.close()

    if num_lines == 0:
        print('File with ids has 0 lines, no recipients for the message')
        return False

    text = input(f'Going to send message {message_to_all_users} to {num_lines} users. Press Enter to confirm: ')
    print(f'Sending...')

    with open('chat_ids.txt') as file:
        for line in file:
            chat_id = int(line[:-1])
            asyncio.run(send_and_wait(TOKEN_STR, chat_id, message_to_all_users))
        file.close()
    print(f'Done')
    return True


def main() -> None:
    check_version()

    if try_send_message_to_all_users():
        return

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
