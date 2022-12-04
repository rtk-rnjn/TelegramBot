from __future__ import annotations

import urllib.parse
from functools import partial
from string import ascii_uppercase
from typing import Any, Callable, Dict, Optional
import aiohttp

from bs4 import BeautifulSoup

from ..utils import ToAsync

try:
    import lxml  # type: ignore

    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"


def get_ele(soup: BeautifulSoup, name: str, **kw: Any):
    return soup.find_all(name, **kw)


async def get_url_response(url: str):
    async with aiohttp.ClientSession() as session:
        return await session.get(url)


@ToAsync()
def sync_async(
    func: Callable[..., Any], *args: Any, **kwargs: Any
) -> Callable[..., Any]:
    """Converts a blocking function to an async function"""

    return func(args, kwargs)


async def python_doc(text: str) -> str:
    """Filters python.org results based on your query"""
    text = text.strip("`")

    url = "https://docs.python.org/3/genindex-all.html"
    alphabet = f"_{ascii_uppercase}"

    response = await get_url_response(url)

    if response.status != 200:
        return f"An error occurred (status code: {response.status}). Retry later."

    soup = BeautifulSoup(
        str(await response.text()), HTML_PARSER
    )  # icantinstalllxmlinheroku

    def soup_match(tag):
        return (
            all(string in tag.text for string in text.strip().split())
            and tag.name == "li"
        )

    elements = await sync_async(soup.find_all, soup_match, limit=10)
    links = [tag.select_one("li > a") for tag in elements]
    links = [link for link in links if link is not None]

    if not links:
        return "No results"

    content = [
        f"[{a.string}](https://docs.python.org/3/{a.get('href')})" for a in links
    ]

    content = f"Results for `{text}` :\n" + "\n".join(content)

    return content


async def _cppreference(language: str, text: str) -> str:
    """Search something on cppreference"""
    text = text.strip("`")

    base_url = (
        f"https://cppreference.com/w/cpp/index.php?title=Special:Search&search={text}"
    )

    url = urllib.parse.quote_plus(base_url, safe=";/?:@&=$,><-[]")

    response = await get_url_response(url)
    if response.status != 200:
        return f"An error occurred (status code: {response.status}). Retry later."

    soup = BeautifulSoup(await response.text(), HTML_PARSER)
    uls = await sync_async(soup.find_all, "ul", class_="mw-search-results")

    if not uls:
        return "No results"

    if language == "C":
        wanted = "w/c/"
        url = (
            "https://wikiprogramming.org/wp-content/uploads/2015/05/c-logo-150x150.png"
        )
    else:
        wanted = "w/cpp/"
        url = "https://isocpp.org/files/img/cpp_logo.png"

    for elem in uls:
        if wanted in elem.select_one("a").get("href"):
            links = elem.find_all("a", limit=10)
            break

    content = [
        f"[{a.string}](https://en.cppreference.com/{a.get('href')})" for a in links
    ]
    content = f"Results for `{text}` :\n" + "\n".join(content)

    return content


c_doc = partial(_cppreference, "C")
cpp_doc = partial(_cppreference, "C++")


async def haskell_doc(text: str) -> str:
    """Search something on wiki.haskell.org"""
    text = text.strip("`")

    snake = "_".join(text.split(" "))

    base_url = f"https://wiki.haskell.org/index.php?title=Special%3ASearch&profile=default&search={snake}&fulltext=Search"
    url = urllib.parse.quote_plus(base_url, safe=";/?:@&=$,><-[]")

    response = await get_url_response(url)
    if response.status != 200:
        return f"An error occurred (status code: {response.status}). Retry later."

    results = BeautifulSoup(await response.text(), HTML_PARSER).find(
        "div", class_="searchresults"
    )

    if results.find("p", class_="mw-search-nonefound") or not results.find(
        "span", id="Page_title_matches"
    ):
        return "No results"

    # Page_title_matches is first
    ul = results.find("ul", "mw-search-results")

    content = []
    ls = await sync_async(ul.find_all, "li", limit=10)
    for li in ls:
        a = li.find("div", class_="mw-search-result-heading").find("a")
        content.append(f"[{a.get('title')}](https://wiki.haskell.org{a.get('href')})")

    return f"Results for `{text}` :\n" + "\n".join(content)
