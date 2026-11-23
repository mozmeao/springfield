# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time
from io import BytesIO
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.base import ContentFile

import pytest
import requests
import responses
from bs4 import BeautifulSoup
from PIL import Image
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError
from wagtail.utils.file import hash_filelike

from springfield.blog.models import BlogArticlePage
from springfield.cms.blocks import (
    YOUTUBE_THUMBNAIL_COLLECTION_NAME,
    YOUTUBE_THUMBNAIL_DEADLINE_ATTR,
    VideoBlock,
    youtube_thumbnail_collection,
)
from springfield.cms.models import SpringfieldImage
from springfield.cms.tests.test_blocks import assert_video_attributes
from springfield.cms.utils import current_request

pytestmark = pytest.mark.django_db

VIDEO_ID = "AbCdEfGhIjK"
OTHER_VIDEO_ID = "ZyXwVuTsRqP"
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


def stored_image(filename, collection=None):
    content = jpeg((0, 0, 255))
    extra = {"collection": collection} if collection else {}
    return SpringfieldImage.objects.create(
        title="A stored image",
        is_decorative=True,
        file=ContentFile(content, name=filename),
        file_hash=hash_filelike(BytesIO(content)),
        **extra,
    )


def stored_thumbnail(video_id=VIDEO_ID):
    return stored_image(f"{video_id}-maxresdefault.jpg", collection=youtube_thumbnail_collection())


def video_data(video_url=YOUTUBE_URL, poster=None, alt="A Firefox demo"):
    return {"video_url": video_url, "alt": alt, "poster": poster.pk if poster else None, "aspect_ratio": ""}


def video_value(**kwargs):
    return VideoBlock().to_python(video_data(**kwargs))


def block_errors(exc_info):
    return {name: [str(message) for message in error.messages] for name, error in exc_info.value.block_errors.items()}


@pytest.fixture
def editor_poster():
    return stored_image("editor-poster.jpg")


@pytest.fixture
def admin_request():
    request = SimpleNamespace(resolver_match=None, user=User.objects.create_user("editor@mozilla.com"))
    token = current_request.set(request)
    yield request
    current_request.reset(token)


@pytest.fixture
def clock():
    now = [0.0]
    with mock.patch("springfield.cms.blocks.time.monotonic", side_effect=lambda: now[0]):
        yield now


@responses.activate
def test_empty_poster_is_filled_with_the_youtube_thumbnail(admin_request):
    mock_thumbnail(MAXRES_URL)

    poster = VideoBlock().clean(video_value())["poster"]

    assert poster.collection.name == YOUTUBE_THUMBNAIL_COLLECTION_NAME
    assert poster.title == "YouTube thumbnail: A Firefox demo"
    assert poster.filename.startswith(f"{VIDEO_ID}-maxresdefault")
    assert poster.is_decorative
    assert poster.uploaded_by_user == admin_request.user
    assert [call.request.url for call in responses.calls] == [MAXRES_URL]


@responses.activate
def test_youtube_thumbnail_falls_back_to_hqdefault():
    responses.add(responses.GET, MAXRES_URL, status=404)
    mock_thumbnail(HQ_URL)

    poster = VideoBlock().clean(video_value())["poster"]

    assert poster.filename.startswith(f"{VIDEO_ID}-hqdefault")
    assert [call.request.url for call in responses.calls] == [MAXRES_URL, HQ_URL]


@responses.activate
def test_youtube_thumbnail_titled_with_video_id_when_alt_is_empty():
    mock_thumbnail(MAXRES_URL)

    poster = VideoBlock().clean_deferred(video_value(alt=""))["poster"]

    assert poster.title == f"YouTube thumbnail: {VIDEO_ID}"


@responses.activate
@pytest.mark.parametrize("video_url", [f"https://youtu.be/{VIDEO_ID}#t=42", f"https://www.youtube.com/shorts/{VIDEO_ID}"])
def test_youtube_thumbnail_for_fragment_and_shorts_links(video_url):
    mock_thumbnail(MAXRES_URL)

    poster = VideoBlock().clean(video_value(video_url=video_url))["poster"]

    assert poster.filename.startswith(f"{VIDEO_ID}-maxresdefault")


@responses.activate
def test_thumbnail_in_the_collection_is_reused_without_downloading():
    thumbnail = stored_thumbnail()

    poster = VideoBlock().clean(video_value())["poster"]

    assert poster == thumbnail
    assert len(responses.calls) == 0


@responses.activate
def test_current_youtube_thumbnail_is_kept_without_downloading():
    thumbnail = stored_thumbnail()

    poster = VideoBlock().clean(video_value(poster=thumbnail))["poster"]

    assert poster == thumbnail
    assert len(responses.calls) == 0


@responses.activate
def test_changing_the_video_replaces_its_thumbnail():
    old_thumbnail = stored_thumbnail(OTHER_VIDEO_ID)
    mock_thumbnail(MAXRES_URL)

    poster = VideoBlock().clean(video_value(poster=old_thumbnail))["poster"]

    assert poster.filename.startswith(f"{VIDEO_ID}-maxresdefault")


def test_changing_to_a_self_hosted_video_removes_the_youtube_thumbnail():
    old_thumbnail = stored_thumbnail()

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(video_url=SELF_HOSTED_URL, poster=old_thumbnail))

    assert list(block_errors(exc_info)) == ["poster"]


@responses.activate
@pytest.mark.parametrize("video_url", [YOUTUBE_URL, SELF_HOSTED_URL])
def test_editors_poster_is_kept_without_downloading(video_url, editor_poster):
    poster = VideoBlock().clean(video_value(video_url=video_url, poster=editor_poster))["poster"]

    assert poster == editor_poster
    assert len(responses.calls) == 0


@responses.activate
def test_image_named_like_a_thumbnail_outside_the_collection_is_the_editors_poster():
    imported_poster = stored_image(f"{OTHER_VIDEO_ID}-maxresdefault.jpg")

    poster = VideoBlock().clean(video_value(poster=imported_poster))["poster"]

    assert poster == imported_poster
    assert len(responses.calls) == 0


def test_publish_requires_a_poster_for_a_self_hosted_video():
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(video_url=SELF_HOSTED_URL))

    assert list(block_errors(exc_info)) == ["poster"]


def test_publish_reports_missing_poster_with_other_errors():
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(video_url=SELF_HOSTED_URL, alt=""))

    assert set(block_errors(exc_info)) == {"alt", "poster"}


@responses.activate
def test_youtube_link_that_is_not_a_video_needs_a_poster():
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(video_url="https://www.youtube.com/@firefox"))

    assert list(block_errors(exc_info)) == ["video_url"]
    assert len(responses.calls) == 0


@responses.activate
def test_youtube_unreachable_reports_on_the_poster_after_one_attempt():
    responses.add(responses.GET, MAXRES_URL, body=requests.ConnectionError("down"))

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value())

    assert list(block_errors(exc_info)) == ["poster"]
    assert [call.request.url for call in responses.calls] == [MAXRES_URL]


@responses.activate
def test_video_without_youtube_thumbnail_asks_for_a_poster():
    responses.add(responses.GET, MAXRES_URL, status=404)
    responses.add(responses.GET, HQ_URL, status=404)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value())

    assert list(block_errors(exc_info)) == ["poster"]


@responses.activate
def test_thumbnail_downloads_stop_when_the_request_is_out_of_time(admin_request):
    setattr(admin_request, YOUTUBE_THUMBNAIL_DEADLINE_ATTR, time.monotonic() - 1)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value())

    assert list(block_errors(exc_info)) == ["poster"]
    assert len(responses.calls) == 0


@responses.activate
def test_fallback_is_skipped_when_the_first_attempt_used_up_the_time(admin_request, clock):
    def slow_not_found(request):
        clock[0] = 11
        return 404, {}, ""

    responses.add_callback(responses.GET, MAXRES_URL, callback=slow_not_found)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value())

    assert list(block_errors(exc_info)) == ["poster"]
    assert [call.request.url for call in responses.calls] == [MAXRES_URL]


@responses.activate
def test_download_stops_when_the_body_runs_past_the_time(admin_request, clock):
    def slow_body(request):
        clock[0] = 11
        return 200, {"Content-Type": "image/jpeg"}, jpeg((255, 0, 0))

    responses.add_callback(responses.GET, MAXRES_URL, callback=slow_body)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value())

    assert list(block_errors(exc_info)) == ["poster"]
    assert not SpringfieldImage.objects.filter(collection__name=YOUTUBE_THUMBNAIL_COLLECTION_NAME).exists()


@responses.activate
def test_storage_failure_reports_on_the_poster():
    mock_thumbnail(MAXRES_URL)

    with mock.patch.object(SpringfieldImage.objects, "create", side_effect=OSError("storage down")):
        with pytest.raises(StructBlockValidationError) as exc_info:
            VideoBlock().clean(video_value())

    assert list(block_errors(exc_info)) == ["poster"]


@responses.activate
def test_draft_saves_without_poster_when_youtube_has_none():
    responses.add(responses.GET, MAXRES_URL, status=404)
    responses.add(responses.GET, HQ_URL, status=404)

    value = VideoBlock().clean_deferred(video_value())

    assert value["poster"] is None


@pytest.mark.parametrize("video_url", ["", SELF_HOSTED_URL, "https://www.youtube.com/@firefox"])
def test_draft_saves_with_incomplete_video(video_url):
    value = VideoBlock().clean_deferred(video_value(video_url=video_url, alt=""))

    assert value["poster"] is None


@responses.activate
def test_blog_hero_video_gets_youtube_thumbnail():
    mock_thumbnail(MAXRES_URL)
    stream_block = BlogArticlePage._meta.get_field("hero_video").stream_block

    value = stream_block.clean(stream_block.to_python([{"type": "video", "value": video_data()}]))

    assert value[0].value["poster"].filename.startswith(f"{VIDEO_ID}-maxresdefault")


def test_blog_hero_video_requires_poster_for_self_hosted_video():
    stream_block = BlogArticlePage._meta.get_field("hero_video").stream_block

    with pytest.raises(StreamBlockValidationError):
        stream_block.clean(stream_block.to_python([{"type": "video", "value": video_data(video_url=SELF_HOSTED_URL)}]))


@pytest.mark.parametrize("video_url", [YOUTUBE_URL, SELF_HOSTED_URL, f"https://www.youtube.com/shorts/{VIDEO_ID}"])
def test_render_with_poster(video_url, editor_poster):
    data = video_data(video_url=video_url, poster=editor_poster)

    soup = BeautifulSoup(VideoBlock().render(VideoBlock().to_python(data)), "html.parser")

    assert_video_attributes(soup.find("div", class_="fl-video"), {"value": data})


@pytest.mark.parametrize("video_url", [YOUTUBE_URL, SELF_HOSTED_URL])
def test_render_without_poster(video_url):
    data = video_data(video_url=video_url)

    soup = BeautifulSoup(VideoBlock().render(VideoBlock().to_python(data)), "html.parser")

    video_element = soup.find("div", class_="fl-video")
    assert_video_attributes(video_element, {"value": data})
    assert not video_element.find("button", class_="fl-video-play").has_attr("data-video-poster")
    assert video_element.find("img", class_="fl-video-poster") is None
