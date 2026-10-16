# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO
from types import SimpleNamespace

from django.core.files.base import ContentFile

import pytest
import requests
import responses
from bs4 import BeautifulSoup
from PIL import Image
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError

from springfield.blog.models import BlogArticlePage
from springfield.cms.blocks import VideoBlock, youtube_video_id
from springfield.cms.models import SpringfieldImage
from springfield.cms.tests.test_blocks import assert_video_attributes
from springfield.cms.utils import current_request

pytestmark = pytest.mark.django_db

VIDEO_ID = "AbCdEfGhIjK"
YOUTUBE_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
SELF_HOSTED_URL = "https://assets.mozilla.net/video/firefox-demo.webm"
MAXRES_URL = f"https://img.youtube.com/vi/{VIDEO_ID}/maxresdefault.jpg"
HQ_URL = f"https://img.youtube.com/vi/{VIDEO_ID}/hqdefault.jpg"


def jpeg(colour):
    buffer = BytesIO()
    Image.new("RGB", (16, 9), colour).save(buffer, "JPEG")
    return buffer.getvalue()


def mock_thumbnail(url, colour=(255, 0, 0)):
    responses.add(responses.GET, url, body=jpeg(colour), content_type="image/jpeg")


def video_data(video_url, poster=None):
    return {"video_url": video_url, "alt": "A Firefox demo", "poster": poster.pk if poster else None, "aspect_ratio": ""}


def video_value(video_url, poster=None):
    return VideoBlock().to_python(video_data(video_url, poster))


@pytest.fixture
def poster():
    return SpringfieldImage.objects.create(title="Editor poster", is_decorative=True, file=ContentFile(jpeg((0, 0, 255)), name="poster.jpg"))


@pytest.fixture
def preview_request():
    token = current_request.set(SimpleNamespace(resolver_match=SimpleNamespace(url_name="preview_on_edit")))
    yield
    current_request.reset(token)


@pytest.mark.parametrize(
    "url, expected",
    [
        (YOUTUBE_URL, VIDEO_ID),
        (f"https://youtu.be/{VIDEO_ID}", VIDEO_ID),
        (f"https://www.youtube.com/watch?v={VIDEO_ID}&t=42", VIDEO_ID),
        (f"https://youtu.be/{VIDEO_ID}?si=abc", VIDEO_ID),
        ("https://www.youtube.com/@firefox", None),
        (f"https://www.youtube.com/embed/{VIDEO_ID}", None),
    ],
)
def test_youtube_video_id(url, expected):
    assert youtube_video_id(url) == expected


@responses.activate
def test_clean_keeps_editor_poster(poster):
    value = VideoBlock().clean(video_value(YOUTUBE_URL, poster))

    assert value["poster"] == poster
    assert len(responses.calls) == 0


@responses.activate
def test_clean_fetches_youtube_thumbnail_when_poster_is_empty():
    mock_thumbnail(MAXRES_URL)

    value = VideoBlock().clean(video_value(YOUTUBE_URL))

    poster = value["poster"]
    assert isinstance(poster, SpringfieldImage)
    assert poster.title == "YouTube thumbnail: A Firefox demo"
    assert poster.is_decorative
    assert [call.request.url for call in responses.calls] == [MAXRES_URL]


@responses.activate
def test_clean_falls_back_to_hqdefault():
    responses.add(responses.GET, MAXRES_URL, status=404)
    mock_thumbnail(HQ_URL)

    value = VideoBlock().clean(video_value(YOUTUBE_URL))

    assert value["poster"] is not None
    assert [call.request.url for call in responses.calls] == [MAXRES_URL, HQ_URL]


@responses.activate
def test_clean_reuses_thumbnail_already_in_library():
    mock_thumbnail(MAXRES_URL)
    mock_thumbnail(MAXRES_URL)

    first = VideoBlock().clean(video_value(YOUTUBE_URL))["poster"]
    second = VideoBlock().clean(video_value(YOUTUBE_URL))["poster"]

    assert first == second
    assert SpringfieldImage.objects.filter(title__startswith="YouTube thumbnail").count() == 1


@responses.activate
def test_clean_asks_for_poster_when_youtube_has_no_thumbnail():
    responses.add(responses.GET, MAXRES_URL, status=404)
    responses.add(responses.GET, HQ_URL, status=404)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(YOUTUBE_URL))

    assert "poster" in exc_info.value.block_errors


@responses.activate
def test_clean_stops_trying_when_youtube_is_unreachable():
    responses.add(responses.GET, MAXRES_URL, body=requests.ConnectionError("down"))

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(YOUTUBE_URL))

    assert "poster" in exc_info.value.block_errors
    assert [call.request.url for call in responses.calls] == [MAXRES_URL]


@responses.activate
def test_clean_skips_fetch_in_preview(preview_request):
    value = VideoBlock().clean(video_value(YOUTUBE_URL))

    assert value["poster"] is None
    assert len(responses.calls) == 0


@responses.activate
def test_clean_rejects_youtube_url_without_video_id(poster):
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(f"https://www.youtube.com/embed/{VIDEO_ID}", poster))

    assert "video_url" in exc_info.value.block_errors
    assert len(responses.calls) == 0


@responses.activate
def test_clean_requires_poster_for_self_hosted_video():
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(SELF_HOSTED_URL))

    assert "poster" in exc_info.value.block_errors
    assert len(responses.calls) == 0


@responses.activate
def test_blog_hero_video_fetches_youtube_thumbnail():
    mock_thumbnail(MAXRES_URL)
    stream_block = BlogArticlePage._meta.get_field("hero_video").stream_block

    value = stream_block.clean(stream_block.to_python([{"type": "video", "value": video_data(YOUTUBE_URL)}]))

    assert isinstance(value[0].value["poster"], SpringfieldImage)


def test_blog_hero_video_rejects_self_hosted_video_without_poster():
    stream_block = BlogArticlePage._meta.get_field("hero_video").stream_block

    with pytest.raises(StreamBlockValidationError):
        stream_block.clean(stream_block.to_python([{"type": "video", "value": video_data(SELF_HOSTED_URL)}]))


@pytest.mark.parametrize("video_url", [YOUTUBE_URL, SELF_HOSTED_URL])
def test_render_with_poster(video_url, poster):
    data = video_data(video_url, poster)

    soup = BeautifulSoup(VideoBlock().render(VideoBlock().to_python(data)), "html.parser")

    assert_video_attributes(soup.find("div", class_="fl-video"), {"value": data})


@pytest.mark.parametrize("video_url", [YOUTUBE_URL, SELF_HOSTED_URL])
def test_render_without_poster(video_url):
    data = video_data(video_url)

    soup = BeautifulSoup(VideoBlock().render(VideoBlock().to_python(data)), "html.parser")

    video_element = soup.find("div", class_="fl-video")
    assert_video_attributes(video_element, {"value": data})
    assert not video_element.find("button", class_="fl-video-play").has_attr("data-video-poster")
    assert video_element.find("img", class_="fl-video-poster") is None
