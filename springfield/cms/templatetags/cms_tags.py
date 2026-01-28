# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from django.conf import settings
from django.utils.safestring import mark_safe

import markdown
from bs4 import BeautifulSoup
from django_jinja import library
from jinja2 import pass_context
from wagtail.rich_text import RichText
from wagtail.templatetags.wagtailcore_tags import richtext as wagtail_richtext

from springfield.cms.models.pages import BASE_UTM_PARAMETERS
from springfield.firefox.templatetags.misc import fxa_button


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
        pattern = re.compile(
            r"^(\w+\.)?((mozilla.org)|(mozillafoundation.org)|(firefox.com))",
            re.IGNORECASE,
        )
        if host and host not in ["www.firefox.com", "firefox.com"] and pattern.match(host):
            query_string = parsed_url.query
            query = parse_qs(query_string)
            query.update(utm_parameters)
            new_query_string = urlencode(query, doseq=True)
            return urlunparse(parsed_url._replace(query=new_query_string))
    return value


@library.filter
def markdown_safe(value: str) -> str:
    """
    Safely processes markdown content by preventing Jinja2 from interpreting
    template syntax within code blocks. This is a workaround for django-jinja-markdown
    issues with code blocks containing template syntax.
    """

    # First, protect code blocks by replacing them with placeholders
    code_blocks = []
    protected_content = value

    # Find all code blocks (both ``` and `)
    def replace_code_block(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    # Protect fenced code blocks
    protected_content = re.sub(r"```[^`]*```", replace_code_block, protected_content, flags=re.DOTALL)

    # Protect inline code
    protected_content = re.sub(r"`[^`]+`", replace_code_block, protected_content)

    # Now process with Jinja2 (this won't affect the protected code blocks)
    # The content is already processed by Jinja2 at this point, so we just need to restore code blocks

    # Restore code blocks
    for i, code_block in enumerate(code_blocks):
        protected_content = protected_content.replace(f"__CODE_BLOCK_{i}__", code_block)

    # Convert to markdown
    md = markdown.Markdown(extensions=["fenced_code", "codehilite", "toc"])
    html = md.convert(protected_content)

    return mark_safe(html)


@library.global_function
def read_markdown_file(file_path: str) -> str:
    """
    Reads a markdown file from the pattern library directory structure.
    This allows markdown files to contain template syntax without Jinja2 trying to execute it.

    Usage in templates:
        {{ read_markdown_file('components/rich_text/MARKDOWN_EXAMPLES.md')|markdown_safe }}

    Args:
        file_path: Path to the markdown file relative to the pattern-library directory

    Returns:
        The file contents as a string, or an error message if the file cannot be read
    """
    try:
        # Get project root (Springfield uses ROOT instead of BASE_DIR)
        project_root = getattr(settings, "ROOT", getattr(settings, "BASE_DIR", None))
        if not project_root:
            return "Error: Could not determine project root directory"

        # Construct the full path from project root to pattern library
        pattern_library_path = os.path.join(project_root, "springfield", "cms", "templates", "pattern-library")
        full_path = os.path.join(pattern_library_path, file_path)

        # Security check: ensure the path is within the pattern library directory
        real_base = os.path.realpath(pattern_library_path)
        real_path = os.path.realpath(full_path)
        if not real_path.startswith(real_base):
            return f"Error: File path '{file_path}' is outside the pattern library directory"

        # Read and return the file contents
        with open(real_path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: Markdown file '{file_path}' not found in pattern library"
    except Exception as e:
        return f"Error reading markdown file '{file_path}': {str(e)}"


@pass_context
@library.filter()
def richtext(context, value: str) -> str:
    """
    Replaces Wagtail's `richtext` filter to:
        - process the custom <fxa> tag with Firefox Account link.
        (See springfield/cms/wagtail_hooks.py for the <fxa> tag registration.)
        - add UTM parameters to external Mozilla links.
    """
    rich_text = wagtail_richtext(value)
    soup = BeautifulSoup(str(rich_text), "html.parser")

    for link in soup.find_all("a"):
        href = link.get("href", "")
        link["href"] = add_utm_parameters(context, href)

    for fxa_tag in soup.find_all("fxa"):
        label = fxa_tag.text
        uid = fxa_tag.get("data-cta-uid", "")
        utm_parameters = context.get(
            "utm_parameters",
            {
                **BASE_UTM_PARAMETERS,
                "utm_campaign": label.lower().replace(" ", "_"),
            },
        )
        entrypoint = f"{utm_parameters.get('utm_source', '')}-{utm_parameters.get('utm_campaign', '')}"
        optional_parameters = {
            "utm_campaign": utm_parameters.get("utm_campaign", ""),
        }
        optional_attributes = {
            "data-cta-uid": uid,
            "data-cta-position": "-".join([context.get("block_position", ""), "fxa-link"]),
            "data-cta-text": context.get("block_text", label),
        }
        # Same parameters as used in the fxa_button component, except the button class
        # (springfield/cms/templates/components/fxa_button.html)
        fxa_link = fxa_button(
            ctx=context,
            entrypoint=entrypoint,
            button_text=label,
            is_button_class=False,
            class_name="fxa-link",
            optional_parameters=optional_parameters,
            optional_attributes=optional_attributes,
        )
        fxa_tag.replace_with(BeautifulSoup(fxa_link, "html.parser"))

    return mark_safe(str(soup))


@pass_context
@library.global_function
def get_pre_footer_cta_snippet(context):
    """
    Retrieves the PreFooterCTASnippet for the current locale.
    Returns the first available snippet for the locale, or None if not found.

    Usage in templates:
        {% set pre_footer_cta = get_pre_footer_cta_snippet() %}
        {% if pre_footer_cta %}
        <include:pre-footer-cta label="{{ pre_footer_cta.label }}" link="{{ pre_footer.link }}" />
        {% endif %}
    """
    from springfield.cms.models.snippets import PreFooterCTASnippet

    locale = None
    if "page" in context and hasattr(context["page"], "locale"):
        locale = context["page"].locale
    elif "self" in context and hasattr(context["self"], "locale"):
        locale = context["self"].locale

    if locale:
        return PreFooterCTASnippet.objects.filter(locale=locale).first()

    return None


@pass_context
@library.global_function
def get_pre_footer_cta_form_snippet(context):
    """
    Retrieves the PreFooterCTAFormSnippet for the current locale.
    Returns the first available snippet for the locale, or None if not found.

    Usage in templates:
        {% set pre_footer_cta_form = get_pre_footer_cta_form_snippet() %}
        {% if pre_footer_cta_form %}
          {% set analytics_text = pre_footer_cta_form.heading|richtext|remove_tags %}
          {% set analytics_position = "pre-footer-cta-form" %}
          {% set analytics_id = pre_footer_cta_form.analytics_id %}
          <include:newsletter-form>
            <include:heading
              level="h2"
              heading_text="{{ pre_footer_cta_form.heading|richtext|remove_p_tag }}"
              subheading_text="{{ pre_footer_cta_form.subheading|richtext|remove_p_tag }}"
            />
           </include:newsletter-form>
        {% endif %}
    """
    from springfield.cms.models.snippets import PreFooterCTAFormSnippet

    locale = None
    if "page" in context and hasattr(context["page"], "locale"):
        locale = context["page"].locale
    elif "self" in context and hasattr(context["self"], "locale"):
        locale = context["self"].locale

    if locale:
        return PreFooterCTAFormSnippet.objects.filter(locale=locale).first()

    return None


@pass_context
@library.global_function
def get_download_firefox_cta_snippet(context):
    """
    Retrieves the DownloadFirefoxCallToActionSnippet for the current locale.
    Returns the first available snippet for the locale, or None if not found.

    Usage in templates:
        {% set download_firefox_cta = get_download_firefox_cta_snippet() %}
        {% if download_firefox_cta %}
            {% set value = download_firefox_cta %}
            {% include "cms/snippets/download-firefox-cta.html" %}
        {% endif %}
    """
    from springfield.cms.models.snippets import DownloadFirefoxCallToActionSnippet

    locale = None
    if "page" in context and hasattr(context["page"], "locale"):
        locale = context["page"].locale
    elif "self" in context and hasattr(context["self"], "locale"):
        locale = context["self"].locale

    if locale:
        return DownloadFirefoxCallToActionSnippet.objects.filter(locale=locale).first()

    return None
