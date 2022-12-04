from __future__ import annotations

from telegram.ext import ContextTypes
from telegram import Update
import telegram

from os import environ

from rtfm._used import execute_run

HELP_COMMANDS = """
/<NAME> <CODE> - Execute code in <NAME> language
"""


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(HELP_COMMANDS)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    return await help(update, context)


async def internal_function(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang, code = tuple(update.message.text.split(" ", 1))
    print(lang, code)
    output = await execute_run(lang[1:], code)

    if output:
        await update.message.reply_text(
            output, parse_mode=telegram.constants.ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text("No output")
