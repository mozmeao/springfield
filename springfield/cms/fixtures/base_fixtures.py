# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile

from PIL import Image, ImageDraw, ImageFont
from wagtail.documents.models import Document
from wagtail.models import Site

from springfield.cms.models import ArticleIndexPage, SpringfieldImage, StructuralPage


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


def get_placeholder_images():
    image = Image.new("RGB", (800, 450), (117, 79, 224))
    dark_image = Image.new("RGB", (800, 450), (255, 138, 80))
    mobile_image = Image.new("RGB", (300, 500), (117, 79, 224))
    dark_mobile_image = Image.new("RGB", (300, 500), (255, 138, 80))

    _draw_numbered_grid(image, cols=3, rows=2)
    _draw_numbered_grid(dark_image, cols=3, rows=2)
    _draw_numbered_grid(mobile_image, cols=2, rows=3)
    _draw_numbered_grid(dark_mobile_image, cols=2, rows=3)

    image_buffer = BytesIO()
    image.save(image_buffer, format="PNG")
    image_buffer.seek(0)
    image, _ = SpringfieldImage.objects.get_or_create(
        id=settings.PLACEHOLDER_IMAGE_ID,
        defaults={
            "title": "Placeholder Image for Testing",
            "file": ContentFile(image_buffer.read(), "placeholder_image.png"),
            "description": "A placeholder image used for testing purposes.",
        },
    )
    image_buffer.seek(0)

    dark_image_buffer = BytesIO()
    dark_image.save(dark_image_buffer, format="PNG")
    dark_image_buffer.seek(0)
    dark_image, _ = SpringfieldImage.objects.get_or_create(
        id=settings.PLACEHOLDER_DARK_IMAGE_ID,
        defaults={
            "title": "Dark Mode Placeholder Image for Testing",
            "file": ContentFile(dark_image_buffer.read(), "dark_placeholder_image.png"),
            "description": "A dark mode placeholder image used for testing purposes.",
        },
    )
    dark_image_buffer.seek(0)

    mobile_image_buffer = BytesIO()
    mobile_image.save(mobile_image_buffer, format="PNG")
    mobile_image_buffer.seek(0)
    mobile_image, _ = SpringfieldImage.objects.get_or_create(
        id=settings.PLACEHOLDER_MOBILE_IMAGE_ID,
        defaults={
            "title": "Placeholder Mobile Image for Testing",
            "file": ContentFile(mobile_image_buffer.read(), "placeholder_image.png"),
            "description": "An placeholder mobile image used for testing purposes.",
        },
    )
    mobile_image_buffer.seek(0)

    dark_mobile_image_buffer = BytesIO()
    dark_mobile_image.save(dark_mobile_image_buffer, format="PNG")
    dark_mobile_image_buffer.seek(0)
    dark_mobile_image, _ = SpringfieldImage.objects.get_or_create(
        id=settings.PLACEHOLDER_DARK_MOBILE_IMAGE_ID,
        defaults={
            "title": "Dark Mode Placeholder Mobile Image for Testing",
            "file": ContentFile(dark_mobile_image_buffer.read(), "dark_placeholder_image.png"),
            "description": "A dark mode mobile placeholder image used for testing purposes.",
        },
    )
    dark_mobile_image_buffer.seek(0)

    return image, dark_image, mobile_image, dark_mobile_image


def get_test_index_page():
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    index_page = StructuralPage.objects.filter(slug="tests-index-page").first()
    if not index_page:
        index_page = StructuralPage(
            slug="tests-index-page",
            title="Tests Index Page",
        )
        root_page.add_child(instance=index_page)
        index_page.save_revision().publish()
    return index_page


def get_2026_test_index_page():
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    index_page = StructuralPage.objects.filter(slug="tests-index-page-2026").first()
    if not index_page:
        index_page = StructuralPage(
            slug="tests-index-page-2026",
            title="Tests Index Page 2026",
        )
        root_page.add_child(instance=index_page)
        index_page.save_revision().publish()
    return index_page


def get_article_index_test_page():
    site = Site.objects.get(is_default_site=True)
    root_page = site.root_page
    index_page = ArticleIndexPage.objects.filter(slug="tests-article-index").first()
    if not index_page:
        index_page = ArticleIndexPage(
            slug="tests-article-index",
            title="Tests Article Index Page",
            sub_title="An index page for testing articles.",
            other_articles_heading="<p data-block-key='c1bc4d7eadf0'>More Articles</p>",
            other_articles_subheading="<p data-block-key='c1bc4d7eadf0'>Explore additional articles below.</p>",
        )
        root_page.add_child(instance=index_page)
    else:
        index_page.sub_title = "An index page for testing articles."
        index_page.other_articles_heading = "<p data-block-key='c1bc4d7eadf0'>More Articles</p>"
        index_page.other_articles_subheading = "<p data-block-key='c1bc4d7eadf0'>Explore additional articles below.</p>"
    index_page.save_revision().publish()
    return index_page


def get_test_document():
    document, _ = Document.objects.get_or_create(
        id=settings.PLACEHOLDER_DOCUMENT_ID,
        defaults={
            "title": "Placeholder Document for Testing",
            "file": ContentFile(b"Test document content", "placeholder_document.txt"),
        },
    )
    return document
