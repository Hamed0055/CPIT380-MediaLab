"""Plain text transformations and escaped, self-contained HTML export."""

from html import escape
import re


MAX_BYTES = 256 * 1024
FONTS = {"Sans serif": "system-ui, sans-serif", "Serif": "Georgia, serif", "Monospace": "monospace"}


# Read text: Decode a UTF-8 text file with optional byte-order mark.
def read_text(payload):
    if len(payload) > MAX_BYTES:
        raise ValueError("Choose a text file up to 256 KB.")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Save the file as UTF-8, then open it again.") from exc
    if "\x00" in text:
        raise ValueError("Choose a plain UTF-8 text file.")
    return text


def uppercase_text(text):
    """Convert letters to uppercase using Python's Unicode mapping."""
    return text.upper()


def lowercase_text(text):
    """Convert letters to lowercase using Python's Unicode mapping."""
    return text.lower()


def titlecase_text(text):
    """Capitalize words using Python's Unicode title-case rule."""
    return text.title()


# Clean whitespace: Collapse spacing inside lines while keeping paragraph breaks.
def clean_whitespace(text):
    normalized = "\n".join(" ".join(line.split()) for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", normalized).strip()


# Find and replace: Replace exact, case-sensitive text.
def find_replace(text, old, new):
    if not old:
        raise ValueError("Enter text to find.")
    matches = text.count(old)
    if len(text) + matches * (len(new) - len(old)) > MAX_BYTES:
        raise ValueError("This replacement would create too much text.")
    return text.replace(old, new)


def count_words(text):
    """Count whitespace-separated tokens."""
    return len(text.split())


def count_characters(text):
    """Count Unicode code points, including whitespace."""
    return len(text)


# Format HTML: Escape the input and interpolate only validated formatting values.
def format_html(text, options):
    font = FONTS.get(options.get("font", "Sans serif"))
    size = options.get("size", 16)
    colour = options.get("colour", "#17243a")
    background = options.get("background", "#ffffff")
    alignment = options.get("alignment", "left")
    spacing = options.get("spacing", "1.5")
    block = options.get("block", "p")
    if (not font or type(size) is not int or not 8 <= size <= 72
            or not all(isinstance(c, str) and re.fullmatch(r"#[a-fA-F0-9]{6}", c) for c in (colour, background))
            or alignment not in ("left", "center", "right") or spacing not in ("1", "1.5", "2")
            or block not in ("p", "h2")):
        raise ValueError("Choose valid formatting options.")
    weight = "bold" if options.get("bold") else "normal"
    italic = "italic" if options.get("italic") else "normal"
    decoration = "underline" if options.get("underline") else "none"
    styles = (
        f"font-family:{font};font-size:{size}px;color:{colour};background-color:{background};"
        f"text-align:{alignment};line-height:{spacing};font-weight:{weight};font-style:{italic};"
        f"text-decoration:{decoration};padding:12px;overflow-wrap:anywhere"
    )
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Preserve formatting under both Streamlit's typography and browser defaults.
    block_style = "font:inherit;color:inherit;text-align:inherit;margin:0 0 .65em"
    paragraphs = [
        f'<{block} style="{block_style}">{escape(paragraph).replace(chr(10), "<br>")}</{block}>'
        for paragraph in re.split(r"\n[ \t]*\n+", normalized)
        if paragraph.strip()
    ]
    return f'<div style="{styles}">{"".join(paragraphs)}</div>'


def generate_html_document(text, options):
    """Wrap the formatted fragment in a complete UTF-8 HTML document."""
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>MediaLab text</title></head><body>{format_html(text, options)}</body></html>\n'
    )
