# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.files.base import ContentFile

import pytest
from bs4 import BeautifulSoup
from wagtail.blocks import StructBlockValidationError
from wagtail.documents.models import Document

from springfield.cms.blocks import AnimationBlock, VideoBlock
from springfield.cms.tests.test_video_block import create_image

pytestmark = [pytest.mark.django_db]

ASSETS_URL = "https://assets.mozilla.net/video/red-pandas.webm"

both_blocks = pytest.mark.parametrize("block_class", [VideoBlock, AnimationBlock])


@pytest.fixture
def webm_document():
    return Document.objects.create(title="Red pandas", file=ContentFile(content=b"WebM video", name="red-pandas.webm"))


@pytest.fixture
def poster():
    return create_image(filename="red-pandas-poster.jpg")


@pytest.fixture
def block_value(poster):
    """Build the value of a Video or Animation block from the given video source fields."""

    def build(block, **video_source):
        return block.to_python({"alt": "Red pandas playing", "poster": poster.id, **video_source})

    return build


def test_video_block_plays_an_uploaded_file(block_value):
    block = VideoBlock()
    # The file is named like a YouTube link. It plays as an uploaded file, not in the YouTube player.
    recap = Document.objects.create(title="Recap", file=ContentFile(content=b"WebM video", name="recap.youtube.com.webm"))
    value = block.clean(block_value(block, video_file=recap.id))

    button = BeautifulSoup(block.render(value), "html.parser").find("button", class_="js-video-play")

    assert button["data-video-type"] == "cdn"
    assert button["data-video-url"] == recap.file.url
    assert button["data-video-url"].endswith(".youtube.com.webm")


def test_animation_block_plays_an_uploaded_file(block_value, webm_document):
    block = AnimationBlock()
    value = block.clean(block_value(block, video_file=webm_document.id))

    source = BeautifulSoup(block.render(value), "html.parser").find("source")

    assert source["src"] == webm_document.file.url


def test_video_block_renders_nothing_after_its_video_document_is_deleted(block_value, webm_document):
    block = VideoBlock()
    document_id = webm_document.id
    webm_document.delete()

    rendered = block.render(block_value(block, video_file=document_id))

    assert rendered.strip() == ""


def test_animation_block_without_a_video_shows_its_poster(block_value, poster):
    block = AnimationBlock(required=False)

    video = BeautifulSoup(block.render(block_value(block)), "html.parser").find("video")

    assert video["poster"] == poster.get_rendition("width-800").url


def test_animation_block_accepts_a_url_without_a_file(block_value):
    block = AnimationBlock()

    value = block.clean(block_value(block, video_url=ASSETS_URL))

    assert value.source_url == ASSETS_URL


@both_blocks
def test_block_rejects_a_file_together_with_a_url(block_class, block_value, webm_document):
    block = block_class()

    with pytest.raises(StructBlockValidationError) as exc_info:
        block.clean(block_value(block, video_file=webm_document.id, video_url=ASSETS_URL))

    assert exc_info.value.block_errors["video_file"].message == "Use either an uploaded video or a video URL, not both."


@both_blocks
def test_block_requires_a_file_or_a_url(block_class, block_value):
    block = block_class()

    with pytest.raises(StructBlockValidationError) as exc_info:
        block.clean(block_value(block))
    draft_value = block.clean_deferred(block_value(block))

    assert exc_info.value.block_errors["video_file"].message == "Upload a video or enter a video URL."
    assert draft_value.source_url == ""


@both_blocks
def test_block_rejects_a_document_that_is_not_a_webm_file(block_class, block_value):
    block = block_class()
    report = Document.objects.create(title="Report", file=ContentFile(content=b"%PDF-1.7", name="report.pdf"))

    with pytest.raises(StructBlockValidationError) as exc_info:
        block.clean(block_value(block, video_file=report.id))

    assert exc_info.value.block_errors["video_file"].message == "This document is not a WebM video. Choose a .webm file."


def test_video_block_needs_a_poster_for_an_uploaded_file(webm_document):
    block = VideoBlock()

    with pytest.raises(StructBlockValidationError) as exc_info:
        block.clean(block.to_python({"video_file": webm_document.id, "alt": "Red pandas playing"}))

    assert exc_info.value.block_errors["poster"].message == "Choose a poster image. Uploaded videos and videos from assets.mozilla.net need one."


def test_optional_animation_block_can_be_left_without_a_video():
    block = AnimationBlock(required=False)

    value = block.clean(block.to_python({}))

    assert value.source_url == ""
