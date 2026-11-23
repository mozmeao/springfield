# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.base import ContentFile

import pytest
import requests
import responses
from bs4 import BeautifulSoup
from freezegun import freeze_time
from PIL import Image
from wagtail.blocks import StructBlockValidationError
from wagtail.utils.file import hash_filelike

from springfield.blog.models import BlogArticlePage
from springfield.cms.blocks import YOUTUBE_THUMBNAIL_COLLECTION_NAME, VideoBlock, get_or_create_youtube_thumbnail_collection
from springfield.cms.models import SpringfieldImage
from springfield.cms.tests.test_blocks import assert_video_attributes
from springfield.cms.utils import current_request

pytestmark = pytest.mark.django_db

VIDEO_ID = "AbCdEfGhIjK"
OTHER_VIDEO_ID = "ZyXwVuTsRqP"
YOUTUBE_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
OTHER_YOUTUBE_URL = f"https://www.youtube.com/watch?v={OTHER_VIDEO_ID}"
YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@firefox"
SELF_HOSTED_URL = "https://assets.mozilla.net/video/firefox-demo.webm"
MAXRES_URL = f"https://img.youtube.com/vi/{VIDEO_ID}/maxresdefault.jpg"
HQ_URL = f"https://img.youtube.com/vi/{VIDEO_ID}/hqdefault.jpg"


def build_jpeg_bytes():
    buffer = BytesIO()
    Image.new("RGB", (16, 9), (255, 0, 0)).save(buffer, "JPEG")
    return buffer.getvalue()


def mock_thumbnail(url):
    responses.add(responses.GET, url, body=build_jpeg_bytes(), content_type="image/jpeg")


def create_image(filename, collection=None):
    content = build_jpeg_bytes()
    collection_kwargs = {"collection": collection} if collection else {}
    return SpringfieldImage.objects.create(
        title="A stored image",
        is_decorative=True,
        file=ContentFile(content, name=filename),
        file_hash=hash_filelike(BytesIO(content)),
        **collection_kwargs,
    )


def create_stored_thumbnail(video_id):
    return create_image(f"{video_id}-maxresdefault.jpg", collection=get_or_create_youtube_thumbnail_collection())


def build_video_data(video_url=YOUTUBE_URL, poster=None, alt="A Firefox demo"):
    return {"video_url": video_url, "alt": alt, "poster": poster.pk if poster else None, "aspect_ratio": ""}


def build_video_value(**kwargs):
    return VideoBlock().to_python(build_video_data(**kwargs))


def get_error_fields(exc_info):
    return set(exc_info.value.block_errors)


@pytest.fixture
def editor_poster():
    return create_image("editor-poster.jpg")


@pytest.fixture
def editor_request():
    request = SimpleNamespace(resolver_match=None, user=User.objects.create_user("editor@mozilla.com"))
    token = current_request.set(request)
    yield request
    current_request.reset(token)


@pytest.fixture(autouse=True)
def mocked_responses():
    """Mock every request, so a test that reaches YouTube without mocking it fails."""
    with responses.mock:
        yield


@pytest.fixture
def frozen_clock():
    """Stops the clock. Move it forward with `frozen_clock.tick(seconds)`."""
    with freeze_time() as frozen_time:
        yield frozen_time


# Filling an empty poster with the YouTube thumbnail


def test_empty_poster_gets_the_youtube_thumbnail(editor_request):
    mock_thumbnail(MAXRES_URL)

    poster = VideoBlock().clean(build_video_value())["poster"]

    assert poster.collection.name == YOUTUBE_THUMBNAIL_COLLECTION_NAME
    assert poster.title == "YouTube thumbnail: A Firefox demo"
    assert poster.filename.startswith(f"{VIDEO_ID}-maxresdefault")
    assert poster.is_decorative
    assert poster.uploaded_by_user == editor_request.user
    assert [call.request.url for call in responses.calls] == [MAXRES_URL]


def test_thumbnail_falls_back_to_hqdefault():
    responses.add(responses.GET, MAXRES_URL, status=404)
    mock_thumbnail(HQ_URL)

    poster = VideoBlock().clean(build_video_value())["poster"]

    assert poster.filename.startswith(f"{VIDEO_ID}-hqdefault")
    assert [call.request.url for call in responses.calls] == [MAXRES_URL, HQ_URL]


def test_thumbnail_is_titled_with_the_video_id_without_alt_text():
    mock_thumbnail(MAXRES_URL)

    # A draft, because publishing needs alt text.
    poster = VideoBlock().clean_deferred(build_video_value(alt=""))["poster"]

    assert poster.title == f"YouTube thumbnail: {VIDEO_ID}"


@pytest.mark.parametrize(
    "video_url",
    [f"https://youtu.be/{VIDEO_ID}#t=42", f"https://www.youtube.com/shorts/{VIDEO_ID}", f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}"],
)
def test_thumbnail_for_other_youtube_links(video_url):
    mock_thumbnail(MAXRES_URL)

    poster = VideoBlock().clean(build_video_value(video_url=video_url))["poster"]

    assert poster.filename.startswith(f"{VIDEO_ID}-maxresdefault")


def test_stored_thumbnail_is_reused_without_downloading():
    stored_thumbnail = create_stored_thumbnail(VIDEO_ID)

    poster = VideoBlock().clean(build_video_value())["poster"]

    assert poster == stored_thumbnail
    assert len(responses.calls) == 0


# Keeping or replacing a poster that is already set


@pytest.mark.parametrize("video_url", [YOUTUBE_URL, SELF_HOSTED_URL])
def test_editors_poster_is_kept(video_url, editor_poster):
    poster = VideoBlock().clean(build_video_value(video_url=video_url, poster=editor_poster))["poster"]

    assert poster == editor_poster
    assert len(responses.calls) == 0


def test_image_named_like_a_thumbnail_outside_the_collection_is_kept():
    imported_poster = create_image(f"{OTHER_VIDEO_ID}-maxresdefault.jpg")

    poster = VideoBlock().clean(build_video_value(poster=imported_poster))["poster"]

    assert poster == imported_poster
    assert len(responses.calls) == 0


def test_thumbnail_of_the_current_video_is_kept():
    stored_thumbnail = create_stored_thumbnail(VIDEO_ID)

    poster = VideoBlock().clean(build_video_value(poster=stored_thumbnail))["poster"]

    assert poster == stored_thumbnail
    assert len(responses.calls) == 0


def test_changing_the_youtube_video_changes_its_thumbnail():
    old_thumbnail = create_stored_thumbnail(OTHER_VIDEO_ID)
    mock_thumbnail(MAXRES_URL)

    poster = VideoBlock().clean(build_video_value(poster=old_thumbnail))["poster"]

    assert poster.filename.startswith(f"{VIDEO_ID}-maxresdefault")


@pytest.mark.parametrize("video_url", [SELF_HOSTED_URL, YOUTUBE_CHANNEL_URL])
def test_changing_to_a_video_without_a_thumbnail_clears_the_old_one(video_url):
    old_thumbnail = create_stored_thumbnail(VIDEO_ID)

    poster = VideoBlock().clean_deferred(build_video_value(video_url=video_url, poster=old_thumbnail))["poster"]

    assert poster is None


# Publishing needs a poster; a draft doesn't


def test_publishing_a_self_hosted_video_needs_a_poster():
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(build_video_value(video_url=SELF_HOSTED_URL, alt=""))

    assert get_error_fields(exc_info) == {"alt", "poster"}


def test_publishing_a_youtube_link_without_a_video_reports_the_link():
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(build_video_value(video_url=YOUTUBE_CHANNEL_URL))

    assert get_error_fields(exc_info) == {"video_url"}
    assert len(responses.calls) == 0


@pytest.mark.parametrize("video_url", ["", SELF_HOSTED_URL, YOUTUBE_CHANNEL_URL])
def test_draft_saves_without_a_poster(video_url):
    value = VideoBlock().clean_deferred(build_video_value(video_url=video_url, alt=""))

    assert value["poster"] is None


def test_blog_hero_video_gets_the_youtube_thumbnail():
    mock_thumbnail(MAXRES_URL)
    stream_block = BlogArticlePage._meta.get_field("hero_video").stream_block

    value = stream_block.clean(stream_block.to_python([{"type": "video", "value": build_video_data()}]))

    assert value[0].value["poster"].filename.startswith(f"{VIDEO_ID}-maxresdefault")


# When the thumbnail can't be stored, publishing reports it on the poster and a draft saves without one


def test_youtube_without_a_thumbnail():
    responses.add(responses.GET, MAXRES_URL, status=404)
    responses.add(responses.GET, HQ_URL, status=404)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(build_video_value())
    draft_value = VideoBlock().clean_deferred(build_video_value())

    assert get_error_fields(exc_info) == {"poster"}
    assert draft_value["poster"] is None


def test_youtube_unreachable_is_tried_once():
    responses.add(responses.GET, MAXRES_URL, body=requests.ConnectionError("down"))

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(build_video_value())

    assert get_error_fields(exc_info) == {"poster"}
    assert [call.request.url for call in responses.calls] == [MAXRES_URL]


def test_storage_failure():
    mock_thumbnail(MAXRES_URL)

    with mock.patch.object(SpringfieldImage.objects, "create", side_effect=OSError("storage down")):
        with pytest.raises(StructBlockValidationError) as exc_info:
            VideoBlock().clean(build_video_value())

    assert get_error_fields(exc_info) == {"poster"}


# One save gets a limited time for all of its thumbnail downloads


def test_downloads_stop_once_a_save_runs_out_of_time(editor_request, frozen_clock):
    def slow_not_found(request):
        frozen_clock.tick(11)
        return 404, {}, ""

    responses.add_callback(responses.GET, MAXRES_URL, callback=slow_not_found)

    with pytest.raises(StructBlockValidationError) as first_video_errors:
        VideoBlock().clean(build_video_value())
    with pytest.raises(StructBlockValidationError) as second_video_errors:
        VideoBlock().clean(build_video_value(video_url=OTHER_YOUTUBE_URL))

    assert get_error_fields(first_video_errors) == {"poster"}
    assert get_error_fields(second_video_errors) == {"poster"}
    assert [call.request.url for call in responses.calls] == [MAXRES_URL]


def test_download_stops_when_the_body_runs_out_of_time(editor_request, frozen_clock):
    def slow_body(request):
        frozen_clock.tick(11)
        return 200, {"Content-Type": "image/jpeg"}, build_jpeg_bytes()

    responses.add_callback(responses.GET, MAXRES_URL, callback=slow_body)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(build_video_value())

    assert get_error_fields(exc_info) == {"poster"}
    assert not SpringfieldImage.objects.filter(collection__name=YOUTUBE_THUMBNAIL_COLLECTION_NAME).exists()


# Rendering


@pytest.mark.parametrize(
    "video_url",
    [YOUTUBE_URL, SELF_HOSTED_URL, f"https://www.youtube.com/shorts/{VIDEO_ID}", f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}"],
)
def test_render_with_poster(video_url, editor_poster):
    data = build_video_data(video_url=video_url, poster=editor_poster)

    soup = BeautifulSoup(VideoBlock().render(VideoBlock().to_python(data)), "html.parser")

    assert_video_attributes(soup.find("div", class_="fl-video"), {"value": data}, expected_video_id=VIDEO_ID)


@pytest.mark.parametrize("video_url", [YOUTUBE_URL, SELF_HOSTED_URL])
def test_render_without_poster(video_url):
    data = build_video_data(video_url=video_url)

    soup = BeautifulSoup(VideoBlock().render(VideoBlock().to_python(data)), "html.parser")

    video_element = soup.find("div", class_="fl-video")
    assert_video_attributes(video_element, {"value": data}, expected_video_id=VIDEO_ID)
    assert not video_element.find("button", class_="fl-video-play").has_attr("data-video-poster")
    assert video_element.find("img", class_="fl-video-poster") is None
