from __future__ import annotations

import re
import urllib.parse
from functools import partial
from typing import Any

from bs4 import BeautifulSoup
from markdownify import MarkdownConverter  # type: ignore
import aiohttp

try:
    import lxml  # type: ignore

    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"


class DocMarkdownConverter(MarkdownConverter):
    def convert_pre(self, el, text):
        """Wrap any codeblocks in `py` for syntax highlighting."""
        code = "".join(el.strings)

        return f"```py\n{code}```"


def markdownify(html: Any):
    return DocMarkdownConverter(bullets="\N{BULLET}").convert(html)


async def get_url_response(url: str):
    async with aiohttp.ClientSession() as session:
        return await session.get(url)


async def _process_mozilla_doc(url: str):
    """
    From a given url from developers.mozilla.org, processes format,
    returns tag formatted content
    """
    response = await get_url_response(url)
    if response.status == 404:
        return "No results"
    if response.status != 200:
        return f"An error occurred (status code: {response.status}). Retry later."

    body = BeautifulSoup(await response.text(), HTML_PARSER).find("body")

    contents = body.find(id="wikiArticle").find(lambda x: x.name == "p" and x.text)
    return markdownify(contents).replace(
        "(/en-US/docs", "(https://developer.mozilla.org/en-US/docs"
    )


async def html_ref(text: str):
    """Displays informations on an HTML tag"""
    text = text.strip("<>`")

    base_url = f"https://developer.mozilla.org/en-US/docs/Web/HTML/Element/{text}"
    url = urllib.parse.quote_plus(base_url, safe=";/?:@&=$,><-[]")

    output = await _process_mozilla_doc(url)
    if not isinstance(output, str):
        # Error message already sent
        return

    return output


async def _http_ref(part, text: str):
    """Displays informations about HTTP protocol"""
    base_url = f"https://developer.mozilla.org/en-US/docs/Web/HTTP/{part}/{text}"
    url = urllib.parse.quote_plus(base_url, safe=";/?:@&=$,><-[]")

    output = await _process_mozilla_doc(url)
    if not isinstance(output, str):
        # Error message already sent
        return

    return output


http_headers = partial(_http_ref, "Headers")
http_methods = partial(_http_ref, "Methods")
http_status = partial(_http_ref, "Status")
csp_directives = partial(_http_ref, "Headers/Content-Security-Policy")


async def _git_main_ref(part: str, text: str):
    """Displays a git help page"""
    text = text.strip("`")

    if part and text == "git":
        # just 'git'
        part = ""
    if not part and not text.startswith("git"):
        # gittutorial, giteveryday...
        part = "git"
    base_url = f"https://git-scm.com/docs/{part}{text}"
    url = urllib.parse.quote_plus(base_url, safe=";/?:@&=$,><-[]")

    response = await get_url_response(url)
    if response.status != 200:
        return f"An error occurred (status code: {response.status}). Retry later."
    if str(response.url) == "https://git-scm.com/docs":
        # Website redirects to home page
        return "No results"

    soup = BeautifulSoup(await response.text(), HTML_PARSER)
    sectors = soup.find_all("div", {"class": "sect1"}, limit=3)

    title = sectors[0].find("p").text

    ls = []
    for tag in sectors[1:]:
        content = "\n".join(
            [markdownify(p) for p in tag.find_all(lambda x: x.name in ["p", "pre"])]
        )
        ls.append(content)

    return f"**{title}**\n\n" + "\n\n".join(ls)


git_ref = partial(_git_main_ref, "git-")
git_tutorial_ref = partial(_git_main_ref, "")


async def sql_ref(text: str):
    """Displays reference on an SQL statement"""
    text = text.strip("`").lower()
    if text in {"check", "unique", "not null"}:
        text += " constraint"
    text = re.sub(" ", "-", text)
    base_url = f"http://www.sqltutorial.org/sql-{text}/"
    url = urllib.parse.quote_plus(base_url, safe=";/?:@&=$,><-[]")
    response = await get_url_response(url)
    if response.status != 200:
        return f"An error occurred (status code: {response.status}). Retry later."

    body = BeautifulSoup(await response.text(), HTML_PARSER).find("body")
    intro = body.find(lambda x: x.name == "h2" and "Introduction to " in x.string)
    title = body.find("h1").string
    ps = []
    for tag in tuple(intro.next_siblings):
        if tag.name == "h2" and tag.text.startswith("SQL "):
            break
        if tag.name == "p":
            ps.append(tag)
    description = "\n".join([markdownify(p) for p in ps])[:2048]
    return f"**{title}**\n\n{description}"


async def haskell_ref(text: str):
    """Displays informations on given Haskell topic"""
    text = text.strip("`")

    snake = "_".join(text.split(" "))

    base_url = f"https://wiki.haskell.org/{snake}"
    url = urllib.parse.quote_plus(base_url, safe=";/?:@&=$,><-[]")

    response = await get_url_response(url)
    if response.status == 404:
        return f"No results for `{text}`"
    if response.status != 200:
        return f"An error occurred (status code: {response.status}). Retry later."

    soup = BeautifulSoup(await response.text(), HTML_PARSER).find("div", id="content")

    title = soup.find("h1", id="firstHeading").string
    description = "\n".join(
        [
            markdownify(p)
            for p in soup.find_all(
                lambda x: x.name in ["p", "li"]
                and tuple(x.parents)[1].name not in ("td", "li"),
                limit=6,
            )
        ]
    )[:2048]

    return f"**{title}**\n\n{description}"
