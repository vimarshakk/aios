"""HTML content parser — extract structured data from raw HTML.

Uses selectolax for fast HTML parsing without a full DOM tree.
Extracts text, links, images, forms, and metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

from selectolax.parser import HTMLParser


@dataclass(frozen=True)
class Link:
    """An extracted hyperlink."""

    href: str
    text: str
    rel: str = ""


@dataclass(frozen=True)
class Image:
    """An extracted image reference."""

    src: str
    alt: str = ""
    width: str = ""
    height: str = ""


@dataclass(frozen=True)
class FormField:
    """A single form input."""

    name: str
    field_type: str
    value: str = ""
    placeholder: str = ""
    required: bool = False


@dataclass(frozen=True)
class FormData:
    """An extracted form."""

    action: str
    method: str
    fields: tuple[FormField, ...]


@dataclass(frozen=True)
class Meta:
    """A page meta tag."""

    name: str
    content: str


@dataclass(frozen=True)
class ParsedPage:
    """Structured content extracted from an HTML page.

    Attributes:
        title: Page title from <title> tag.
        text: Visible text content (stripped, collapsed whitespace).
        links: All <a href="..."> links.
        images: All <img> tags.
        forms: All <form> tags with their fields.
        meta: All <meta> tags.
        charset: Detected or declared charset.
        language: Document language from <html lang="...">.
    """

    title: str = ""
    text: str = ""
    links: tuple[Link, ...] = ()
    images: tuple[Image, ...] = ()
    forms: tuple[FormData, ...] = ()
    meta: tuple[Meta, ...] = ()
    charset: str = ""
    language: str = ""


def parse_html(html: str) -> ParsedPage:
    """Parse raw HTML into a structured ParsedPage.

    Args:
        html: Raw HTML string.

    Returns:
        ParsedPage with extracted content.
    """
    tree = HTMLParser(html)

    title = ""
    title_tag = tree.css_first("title")
    if title_tag:
        title = title_tag.text(strip=True) or ""

    text = ""
    body = tree.body
    if body:
        text = body.text(strip=True)

    links: list[Link] = []
    for tag in tree.css("a[href]"):
        href = tag.attributes.get("href", "")
        rel = tag.attributes.get("rel", "")
        if href:
            links.append(Link(href=href, text=tag.text(strip=True), rel=rel))

    images = [
        Image(
            src=tag.attributes.get("src", ""),
            alt=tag.attributes.get("alt", ""),
            width=tag.attributes.get("width", ""),
            height=tag.attributes.get("height", ""),
        )
        for tag in tree.css("img[src]")
    ]

    forms: list[FormData] = []
    for form_tag in tree.css("form"):
        action = form_tag.attributes.get("action", "")
        method = (form_tag.attributes.get("method", "GET")).upper()
        fields: list[FormField] = []
        for inp in form_tag.css("input, select, textarea"):
            name = inp.attributes.get("name", "")
            if not name:
                continue
            fields.append(
                FormField(
                    name=name,
                    field_type=inp.attributes.get("type", "text"),
                    value=inp.attributes.get("value", ""),
                    placeholder=inp.attributes.get("placeholder", ""),
                    required="required" in inp.attributes,
                ),
            )
        forms.append(FormData(action=action, method=method, fields=tuple(fields)))

    meta: list[Meta] = []
    for tag in tree.css("meta[name], meta[property]"):
        name = tag.attributes.get("name", "") or tag.attributes.get("property", "")
        content = tag.attributes.get("content", "")
        if name:
            meta.append(Meta(name=name, content=content))

    charset = ""
    charset_tag = tree.css_first("meta[charset]")
    if charset_tag:
        charset = charset_tag.attributes.get("charset", "")

    language = ""
    html_tag = tree.css_first("html[lang]")
    if html_tag:
        language = html_tag.attributes.get("lang", "")

    return ParsedPage(
        title=title,
        text=text,
        links=tuple(links),
        images=tuple(images),
        forms=tuple(forms),
        meta=tuple(meta),
        charset=charset,
        language=language,
    )


__all__ = [
    "FormData",
    "FormField",
    "Image",
    "Link",
    "Meta",
    "ParsedPage",
    "parse_html",
]
