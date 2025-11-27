"""
Utility helper functions.
"""

from urllib.request import urlopen

from bs4 import BeautifulSoup


def print_from_link(url: str) -> None:
    """
    Extract and print text content from a URL.

    Args:
        url: URL to fetch and parse
    """
    html = urlopen(url).read()
    soup = BeautifulSoup(html, features="html.parser")

    # Remove script and style elements
    for element in soup(["script", "style"]):
        element.extract()

    # Get text
    text = soup.get_text()

    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)

    print(text)
