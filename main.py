from __future__ import annotations

from os import environ

from telegram.ext import CommandHandler, Application
from dotenv import load_dotenv
import re
from commands import start, internal_function

from colorama import init, Fore, Style

init()

print(f"{Fore.GREEN}Loading Environment Variable...{Style.RESET_ALL}")
load_dotenv()

TOKEN = environ["TOKEN"]
REGEX_MATCH = r"([A-Za-z0-9])+"

with open("lang.txt") as f:
    languages = [
        st for st in set(f.read().split("\n")) if st and re.fullmatch(REGEX_MATCH, st)
    ]


if __name__ == "__main__":
    print(f"{Fore.GREEN}Starting bot...{Style.RESET_ALL}")
    print()
    application = Application.builder().token(TOKEN).build()

    s_count, e_count = 0, 0
    for lang in languages:
        
        try:
            application.add_handler(CommandHandler(lang, internal_function))
            print(f"{Fore.GREEN}Added handler for {lang}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Failed to add handler for {lang}{Style.RESET_ALL}")
            print(e)
            e_count += 1
        else:
            s_count += 1
    
    print()
    print(f"{Fore.GREEN}Total handlers added: {s_count}{Style.RESET_ALL}")
    print(f"{Fore.RED}Total handlers failed: {e_count}{Style.RESET_ALL}")
    print()

    print(f"{Fore.GREEN}Added handlers for all languages{Style.RESET_ALL}")
    application.add_handler(CommandHandler(["start", "help"], start))
    print()
    print(f"{Fore.GREEN}Added handler for start and help{Style.RESET_ALL}")

    application.run_polling()
