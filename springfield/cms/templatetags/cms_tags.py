# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.utils.safestring import mark_safe

from bs4 import BeautifulSoup
from django_jinja import library
from wagtail.rich_text import RichText


@library.filter
def remove_p_tag(value: str) -> str:
    rich_text = RichText(value)
    html_content = str(rich_text.source)
    soup = BeautifulSoup(html_content, "html.parser")
    content = ""
    if soup and soup.p:
        content = "<br/>".join("".join(str(c) for c in tag.contents) for tag in soup.find_all("p"))
    return mark_safe(content)
