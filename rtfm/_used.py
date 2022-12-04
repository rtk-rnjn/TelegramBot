from __future__ import annotations

import contextlib
import re
from typing import Any, Dict, List

from yaml import safe_load as yaml_load  # type: ignore

from ._tio import Tio
from utils import mystbin

paste_client = mystbin.Client()

with open("lang.txt") as f:
    languages = f.read().split("\n")

wrapping: Dict[str, str] = {
    "c": "#include <stdio.h>\nint main() {code}",
    "cpp": "#include <iostream>\nint main() {code}",
    "cs": "using System;class Program {static void Main(string[] args) {code}}",
    "java": "public class Main {public static void main(String[] args) {code}}",
    "rust": "fn main() {code}",
    "d": "import std.stdio; void main(){code}",
    "kotlin": "fun main(args: Array<String>) {code}",
}

with open("default_langs.yml", "r") as file:
    default_langs = yaml_load(file)


async def execute_run(
    language: str,
    code: str,
) -> str:  # sourcery skip: low-code-quality
    # Powered by tio.run

    options = {"--stats": False, "--wrapped": False}

    lang = language.strip("`").lower()

    optionsAmount = len(options)

    # Setting options and removing them from the beginning of the command
    # options may be separated by any single whitespace, which we keep in the list
    code: List[str] = re.split(r"(\s)", code, maxsplit=optionsAmount)

    for option in options:
        if option in code[: optionsAmount * 2]:
            options[option] = True
            i = code.index(option)
            code.pop(i)
            code.pop(i)  # remove following whitespace character

    code = "".join(code)

    compilerFlags = []
    commandLineOptions = []
    args = []
    inputs = []

    lines = code.split("\n")
    code = []
    for line in lines:
        if line.startswith("input "):
            inputs.append(" ".join(line.split(" ")[1:]).strip("`"))
        elif line.startswith("compiler-flags "):
            compilerFlags.extend(line[15:].strip("`").split(" "))
        elif line.startswith("command-line-options "):
            commandLineOptions.extend(line[21:].strip("`").split(" "))
        elif line.startswith("arguments "):
            args.extend(line[10:].strip("`").split(" "))
        else:
            code.append(line)

    inputs = "\n".join(inputs)

    code: str = "\n".join(code)

    # common identifiers, also used in highlight.js and thus discord codeblocks
    quickmap: Dict[str, str] = {
        "asm": "assembly",
        "c#": "cs",
        "c++": "cpp",
        "csharp": "cs",
        "f#": "fs",
        "fsharp": "fs",
        "js": "javascript",
        "nimrod": "nim",
        "py": "python",
        "q#": "qs",
        "rs": "rust",
        "sh": "bash",
        "python": "python",
    }

    lang = quickmap.get(lang) or lang

    if lang in default_langs:
        lang = default_langs[lang]
    if lang not in languages:  # this is intentional
        matches = []
        i = 0
        for language in languages:
            if language.startswith(lang[:3]):
                matches.append(language)
                i += 1
                if i == 10:
                    break
        output = f"`{lang}` not available."
        if matches := "\n".join(matches):
            output = f"{output} Did you mean:\n{matches}"

        return output

    code = code.strip("`")

    if "\n" in code:
        firstLine = code.splitlines()[0]
        if re.fullmatch(r"([0-9A-z]*)\b", firstLine):
            code = code[len(firstLine) + 1 :]

    if options["--wrapped"]:
        if not (any(map(lambda x: lang.split("-")[0] == x, wrapping))) or lang in (
            "cs-mono-shell",
            "cs-csi",
        ):
            return f"`{lang}` cannot be wrapped."

        for beginning in wrapping:
            if lang.split("-")[0] == beginning:
                code = wrapping[beginning].replace("code", code)
                break

    tio = Tio(
        lang,
        code,
        compilerFlags=compilerFlags,
        inputs=inputs,
        commandLineOptions=commandLineOptions,
        args=args,
    )

    result = await tio.send()

    if not options["--stats"]:
        with contextlib.suppress(ValueError):
            start = result.rindex("Real time: ")
            end = result.rindex("%\nExit code: ")
            result = result[:start] + result[end + 2 :]
    if len(result) > 4000 or result.count("\n") > 100:

        link = await paste_client.post(result)

        if link is None:
            output = (
                "Your output was too long, but I couldn't make an online bin out of it."
            )
        else:
            output = f"Output was too long (more than 4000 characters or 100 lines) so I put it here: {link.url}"

        return output

    zero = "\N{zero width space}"
    output = re.sub("```", f"{zero}`{zero}`{zero}`{zero}", result)

    # p, as placeholder, prevents Discord from taking the first line
    # as a language identifier for markdown and remove it

    return f"```\n{output}\n```"


def get_raw(link: str) -> str:
    """Returns the url for raw version on a hastebin-like"""
    link = link.strip("<>/")  # Allow for no-embed links

    authorized = (
        "https://hastebin.com",
        "https://gist.github.com",
        "https://gist.githubusercontent.com",
    )

    if not any(link.startswith(url) for url in authorized):
        return f"Bot only accept links from {', '.join(authorized)}. (Starting with 'http')."

    domain = link.split("/")[2]

    if domain == "hastebin.com":
        if "/raw/" in link:
            return link
        token = link.split("/")[-1]
        if "." in token:
            token = token[: token.rfind(".")]  # removes extension
        return f"https://hastebin.com/raw/{token}"
    # Github uses redirection so raw -> usercontent and no raw -> normal
    # We still need to ensure we get a raw version after this potential redirection
    return link if "/raw" in link else f"{link}/raw"
