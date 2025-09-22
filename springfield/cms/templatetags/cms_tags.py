from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe
from wagtail.rich_text import RichText
from django_jinja import library


@library.filter
def remove_p_tag(value: str) -> str:
    rich_text = RichText(value)
    html_content = str(rich_text.source)
    soup = BeautifulSoup(html_content, "html.parser")
    content = ""
    if soup and soup.p:
        content = "<br/>".join(
            "".join(str(c) for c in tag.contents) for tag in soup.find_all("p")
        )
    return mark_safe(content)
