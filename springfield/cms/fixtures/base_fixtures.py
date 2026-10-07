# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO
from typing import NamedTuple
from uuid import uuid4

from django.core.files.base import ContentFile

from PIL import Image, ImageDraw, ImageFont
from wagtail.documents.models import Document
from wagtail.models import Locale, Site

from springfield.cms.models import ArticleIndexPage, SpringfieldImage
from springfield.cms.models.pages import FlareDocsIndexPage

PLACEHOLDER_IMAGE_TITLE = "Placeholder Image for Testing"
PLACEHOLDER_DARK_IMAGE_TITLE = "Dark Mode Placeholder Image for Testing"
PLACEHOLDER_MOBILE_IMAGE_TITLE = "Placeholder Mobile Image for Testing"
PLACEHOLDER_DARK_MOBILE_IMAGE_TITLE = "Dark Mode Placeholder Mobile Image for Testing"
PLACEHOLDER_DOCUMENT_TITLE = "Placeholder Document for Testing"

SHOW_TO_ALL = {"platforms": [], "firefox": "", "auth_state": "", "default_browser": ""}

EMPTY_IMAGE_VARIANTS = {
    "image": None,
    "image_alt": "",
    "settings": {
        "dark_mode_image": None,
        "mobile_image": None,
        "dark_mode_mobile_image": None,
    },
}


def with_fresh_ids(blocks):
    """Return a rebuilt copy of StreamField fixture data with every block ``id``
    replaced by a freshly generated UUID.

    Fixture block data uses hardcoded ids. Embedding the same generated block
    more than once in a page (e.g. ``cards * 2`` or reusing a shared button dict
    across cards) produces duplicate ids, which collapse wagtail-localize segment
    paths and break translation. Wrapping reused block data in this helper keeps
    every id unique within the page.

    The structure is rebuilt node-by-node (rather than ``deepcopy``d) so that
    aliased objects — e.g. the repeated entries created by ``list * 2`` — become
    independent and each occurrence gets its own id."""
    if isinstance(blocks, dict):
        return {key: (str(uuid4()) if key == "id" else with_fresh_ids(value)) for key, value in blocks.items()}
    if isinstance(blocks, list):
        return [with_fresh_ids(item) for item in blocks]
    return blocks


def get_or_create_page(model, *, slug, parent, defaults=None, **lookup):
    """Fetch or create the en-US page of ``model`` with ``slug`` under ``parent``.

    Always scopes the lookup and creation to the en-US locale so fixtures operate
    on the source-locale page and never accidentally pick up a translated variant
    with the same slug."""
    en_us = Locale.objects.get(language_code="en-US")
    page = model.objects.child_of(parent).filter(slug=slug, locale=en_us, **lookup).first()
    if page is None:
        page = model(slug=slug, locale=en_us, **lookup, **(defaults or {}))
        parent.add_child(instance=page)
    return page


def _draw_numbered_grid(image, cols, rows):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    cell_w = width / cols
    cell_h = height / rows
    font = ImageFont.load_default(size=int(min(cell_w, cell_h) // 3))

    for col in range(1, cols):
        x = round(col * cell_w)
        draw.line([(x, 0), (x, height)], fill="white", width=3)
    for row in range(1, rows):
        y = round(row * cell_h)
        draw.line([(0, y), (width, y)], fill="white", width=3)

    for row in range(rows):
        for col in range(cols):
            num = str(row * cols + col + 1)
            cx = (col + 0.5) * cell_w
            cy = (row + 0.5) * cell_h
            bbox = draw.textbbox((0, 0), num, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((cx - tw / 2, cy - th / 2), num, fill="white", font=font)


class PlaceholderImages(NamedTuple):
    image: SpringfieldImage
    dark_image: SpringfieldImage
    mobile_image: SpringfieldImage
    dark_mobile_image: SpringfieldImage


def get_or_create_placeholder_image(*, title, description, filename, size, color, grid) -> SpringfieldImage:
    """Fetch the placeholder image with ``title``, drawing and saving it only when it doesn't exist yet."""
    image = SpringfieldImage.objects.filter(title=title).first()
    if image is None:
        canvas = Image.new("RGB", size, color)
        _draw_numbered_grid(canvas, *grid)
        buffer = BytesIO()
        canvas.save(buffer, format="PNG")
        image = SpringfieldImage.objects.create(title=title, description=description, file=ContentFile(buffer.getvalue(), filename))
    return image


def get_placeholder_images() -> PlaceholderImages:
    return PlaceholderImages(
        image=get_or_create_placeholder_image(
            title=PLACEHOLDER_IMAGE_TITLE,
            description="A placeholder image used for testing purposes.",
            filename="placeholder_image.png",
            size=(800, 450),
            color=(117, 79, 224),
            grid=(3, 2),
        ),
        dark_image=get_or_create_placeholder_image(
            title=PLACEHOLDER_DARK_IMAGE_TITLE,
            description="A dark mode placeholder image used for testing purposes.",
            filename="dark_placeholder_image.png",
            size=(800, 450),
            color=(255, 138, 80),
            grid=(3, 2),
        ),
        mobile_image=get_or_create_placeholder_image(
            title=PLACEHOLDER_MOBILE_IMAGE_TITLE,
            description="A placeholder mobile image used for testing purposes.",
            filename="placeholder_image.png",
            size=(300, 500),
            color=(117, 79, 224),
            grid=(2, 3),
        ),
        dark_mobile_image=get_or_create_placeholder_image(
            title=PLACEHOLDER_DARK_MOBILE_IMAGE_TITLE,
            description="A dark mode mobile placeholder image used for testing purposes.",
            filename="dark_placeholder_image.png",
            size=(300, 500),
            color=(255, 138, 80),
            grid=(2, 3),
        ),
    )


def get_image_variants() -> dict:
    """Image block value using the placeholder image with all its dark mode and mobile variants."""
    placeholder_images = get_placeholder_images()
    return {
        "image": placeholder_images.image.id,
        "image_alt": "A numbered grid, standing in for a real image",
        "settings": {
            "dark_mode_image": placeholder_images.dark_image.id,
            "mobile_image": placeholder_images.mobile_image.id,
            "dark_mode_mobile_image": placeholder_images.dark_mobile_image.id,
        },
    }


def get_image_media(block_id) -> list[dict]:
    """Media stream holding one image block with the placeholder image and all its variants."""
    return [{"type": "image", "value": get_image_variants(), "id": block_id}]


def get_flare_docs_index_page():
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    index_page = get_or_create_page(
        FlareDocsIndexPage,
        slug="flare-docs",
        parent=root_page,
        defaults={
            "title": "Flare Docs - Index",
            "search_description": "This is the base page for Flare 26's samples and docs.",
        },
    )
    index_page.save_revision().publish()
    return index_page


def get_flare_blocks_docs_page():
    index_page = get_flare_docs_index_page()
    blocks_docs_page = index_page.get_children().filter(slug="blocks").first()
    if not blocks_docs_page:
        blocks_docs_page = FlareDocsIndexPage(
            slug="blocks", title="Flare Docs - Blocks", search_description="This is the base page for Flare 26's CMS block samples and docs."
        )
        index_page.add_child(instance=blocks_docs_page)
        blocks_docs_page.save_revision().publish()
    return blocks_docs_page


def get_flare_pages_docs_page():
    index_page = get_flare_docs_index_page()
    pages_docs_page = index_page.get_children().filter(slug="sample-pages").first()
    if not pages_docs_page:
        pages_docs_page = FlareDocsIndexPage(
            slug="sample-pages", title="Flare Docs - Sample Pages", search_description="This is the base page for Flare 26's CMS page samples."
        )
        index_page.add_child(instance=pages_docs_page)
        pages_docs_page.save_revision().publish()
    return pages_docs_page


def get_flare_snippets_docs_page():
    index_page = get_flare_docs_index_page()
    snippets_docs_page = index_page.get_children().filter(slug="snippets").first()
    if not snippets_docs_page:
        snippets_docs_page = FlareDocsIndexPage(
            slug="snippets",
            title="Flare Docs - Snippets",
            search_description="This is the base page for Flare 26's CMS snippet samples and docs.",
        )
        index_page.add_child(instance=snippets_docs_page)
        snippets_docs_page.save_revision().publish()
    return snippets_docs_page


def get_article_index_test_page():
    root_page = get_flare_pages_docs_page()
    index_page = get_or_create_page(
        ArticleIndexPage,
        slug="tests-article-index",
        parent=root_page,
        defaults={
            "title": "Article Index Page",
            "sub_title": "An index page for testing articles.",
            "other_articles_heading": "<p data-block-key='c1bc4d7eadf0'>More Articles</p>",
            "other_articles_subheading": "<p data-block-key='c1bc4d7eadf0'>Explore additional articles below.</p>",
        },
    )
    index_page.sub_title = "An index page for testing articles."
    index_page.other_articles_heading = "<p data-block-key='c1bc4d7eadf0'>More Articles</p>"
    index_page.other_articles_subheading = "<p data-block-key='c1bc4d7eadf0'>Explore additional articles below.</p>"
    index_page.save_revision().publish()
    return index_page


def get_test_document():
    document = Document.objects.filter(title=PLACEHOLDER_DOCUMENT_TITLE).first()
    if document is None:
        document = Document.objects.create(
            title=PLACEHOLDER_DOCUMENT_TITLE,
            file=ContentFile(b"Test document content", "placeholder_document.txt"),
        )
    return document
