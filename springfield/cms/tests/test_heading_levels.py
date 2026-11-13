# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from wagtail.models import Site

from springfield.cms.fixtures.banner_fixtures import get_banner_test_page
from springfield.cms.fixtures.intro_fixtures import get_intro_test_page
from springfield.cms.fixtures.kit_banner_fixtures import get_kit_banner_test_page
from springfield.cms.tests.factories import ArticleDetailPageFactory

pytestmark = [pytest.mark.django_db]

NAMED_SIZE = re.compile(r"\bfl-heading-(?:3xl|2xl|xl|lg|md|sm|xs|2xs)\b")
# A size class assembled at render time, other than the level class.
BUILT_SIZE = re.compile(r"fl-heading-(?!size-)\{\{|['\"]fl-heading-['\"]\s*~")
TEMPLATES = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "get_page, block_class",
    [(get_banner_test_page, "fl-banner"), (get_kit_banner_test_page, "fl-banner-kit"), (get_intro_test_page, "fl-intro")],
    ids=["banner", "kit-banner", "intro"],
)
def test_first_block_heading_is_the_h1_and_sizes_by_level(get_page, block_class, index_page, placeholder_images, rf):
    page = get_page()

    response = page.serve(rf.get(page.get_full_url()))

    assert response.status_code == 200
    soup = BeautifulSoup(response.content, "html.parser")
    h1s = soup.find_all("h1")
    assert len(h1s) == 1
    assert "fl-heading-size-1" in h1s[0]["class"]
    block_headings = [heading for block in soup.find_all(class_=block_class) for heading in block.find_all(re.compile(r"^h[1-6]$"))]
    for heading in block_headings:
        classes = " ".join(heading.get("class", []))
        assert not NAMED_SIZE.search(classes), f"{heading.name} carries a named size: {classes}"
        if heading.name == "h2" and "fl-heading" in heading.get("class", []):
            assert "fl-heading-size-2" in heading["class"]


def test_article_title_uses_the_small_h1(rf):
    page = ArticleDetailPageFactory(parent=Site.objects.get(is_default_site=True).root_page)

    response = page.serve(rf.get(page.get_full_url()))

    assert response.status_code == 200
    h1 = BeautifulSoup(response.content, "html.parser").find("h1")
    assert "fl-heading-size-1-small" in h1["class"]


def test_no_template_passes_a_named_size_to_a_heading():
    offenders = []
    for path in TEMPLATES.glob("**/templates/**/*.html"):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            tag = re.search(r"<h[1-6]\b[^>]*class=\"([^\"]*)\"", line)
            arg = re.search(r"heading_size\s*=\s*[\"']([^\"']*)[\"']", line)
            if BUILT_SIZE.search(line) or any(match and NAMED_SIZE.search(match.group(1)) for match in (tag, arg)):
                offenders.append(f"{path.relative_to(TEMPLATES)}:{number}")
    assert not offenders, "Headings size by level; remove these size classes: " + ", ".join(offenders)
