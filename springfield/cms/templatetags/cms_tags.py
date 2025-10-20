# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from django.utils.safestring import mark_safe

from bs4 import BeautifulSoup
from django_jinja import library
from jinja2 import pass_context
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


@library.filter
def remove_tags(value: str) -> str:
    rich_text = RichText(value)
    html_content = str(rich_text.source)
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()


@pass_context
@library.filter
def add_utm_parameters(context: dict, value: str) -> str:
    """
    Appends UTM parameters to URLs that point to *.mozilla.org, *.mozillafoundation.org,
    and *.firefox.com domains, except for www.firefox.com.
    """

    utm_parameters = context.get("utm_parameters", {})
    if utm_parameters and value:
        parsed_url = urlparse(value)
        host = ""
        if value.startswith(("http://", "https://", "//")):
            host = parsed_url.netloc
        # Allow for schemeless URLs like "www.example.com/page"
        elif parsed_url.path:
            host = parsed_url.path.split("/")[0]
        pattern = re.compile(r"^(\w+\.)?((mozilla.org)|(mozillafoundation.org)|(firefox.com))", re.IGNORECASE)
        if host and host not in ["www.firefox.com", "firefox.com"] and pattern.match(host):
            query_string = parsed_url.query
            query = parse_qs(query_string)
            query.update(utm_parameters)
            new_query_string = urlencode(query)
            return urlunparse(parsed_url._replace(query=new_query_string))
    return value
