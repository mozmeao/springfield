# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os

from django.conf import settings
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


@library.filter
def remove_tags(value: str) -> str:
    rich_text = RichText(value)
    html_content = str(rich_text.source)
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()


@library.filter
def markdown_safe(value: str) -> str:
    """
    Safely processes markdown content by preventing Jinja2 from interpreting
    template syntax within code blocks. This is a workaround for django-jinja-markdown
    issues with code blocks containing template syntax.
    """
    import re

    import markdown

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
    md = markdown.Markdown(extensions=["fenced_code", "codehilite"])
    html = md.convert(protected_content)

    return mark_safe(html)


@library.global_function
def read_markdown_file(file_path: str) -> str:
    """
    Reads a markdown file from the pattern library directory structure.
    This allows markdown files to contain template syntax without Jinja2 trying to execute it.

    Usage in templates:
        {{ read_markdown_file('components/markdown/MARKDOWN_EXAMPLES.md')|markdown_safe }}

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
