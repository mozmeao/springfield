# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time
from io import BytesIO
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth.models import AnonymousUser, User
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
    POSTER_SOURCE_UPLOAD,
    POSTER_SOURCE_YOUTUBE,
    YOUTUBE_THUMBNAIL_DEADLINE_ATTR,
    VideoBlock,
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


def stored_image(filename, colour=(0, 0, 255)):
    content = jpeg(colour)
    return SpringfieldImage.objects.create(
        title="A stored image",
        is_decorative=True,
        file=ContentFile(content, name=filename),
        file_hash=hash_filelike(BytesIO(content)),
    )


def video_data(video_url=YOUTUBE_URL, poster_source=POSTER_SOURCE_YOUTUBE, poster=None, alt="A Firefox demo"):
    return {"video_url": video_url, "alt": alt, "poster_source": poster_source, "poster": poster.pk if poster else None, "aspect_ratio": ""}


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
def preview_request():
    token = current_request.set(SimpleNamespace(resolver_match=SimpleNamespace(url_name="preview_on_edit"), user=AnonymousUser()))
    yield
    current_request.reset(token)


@pytest.mark.parametrize(
    "stored, expected",
    [
        ({"video_url": YOUTUBE_URL, "alt": "Demo", "poster": 1}, POSTER_SOURCE_UPLOAD),
        ({"video_url": YOUTUBE_URL, "alt": "Demo", "poster": None}, POSTER_SOURCE_YOUTUBE),
        ({"video_url": YOUTUBE_URL, "alt": "Demo", "poster_source": POSTER_SOURCE_YOUTUBE, "poster": 1}, POSTER_SOURCE_YOUTUBE),
    ],
)
def test_blocks_saved_before_the_poster_choice_keep_their_poster(stored, expected):
    assert VideoBlock().to_python(stored)["poster_source"] == expected
    assert VideoBlock().bulk_to_python([stored])[0]["poster_source"] == expected


@responses.activate
def test_youtube_thumbnail_is_downloaded_and_stored_on_save(admin_request):
    mock_thumbnail(MAXRES_URL)

    poster = VideoBlock().clean(video_value())["poster"]

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
def test_current_youtube_thumbnail_is_kept_without_downloading():
    thumbnail = stored_image(f"{VIDEO_ID}-hqdefault.jpg")

    poster = VideoBlock().clean(video_value(poster=thumbnail))["poster"]

    assert poster == thumbnail
    assert len(responses.calls) == 0


@responses.activate
def test_widescreen_thumbnail_already_in_library_is_reused_without_downloading():
    thumbnail = stored_image(f"{VIDEO_ID}-maxresdefault.jpg")

    poster = VideoBlock().clean(video_value())["poster"]

    assert poster == thumbnail
    assert len(responses.calls) == 0


@responses.activate
def test_downloaded_thumbnail_matching_a_library_image_reuses_it():
    library_image = stored_image(f"{VIDEO_ID}-hqdefault.jpg", colour=(255, 0, 0))
    responses.add(responses.GET, MAXRES_URL, status=404)
    mock_thumbnail(HQ_URL, colour=(255, 0, 0))

    poster = VideoBlock().clean(video_value())["poster"]

    assert poster == library_image


@responses.activate
def test_same_bytes_under_another_name_are_stored_as_this_videos_thumbnail():
    stored_image("kit-video.jpg", colour=(255, 0, 0))
    mock_thumbnail(MAXRES_URL, colour=(255, 0, 0))

    poster = VideoBlock().clean(video_value())["poster"]

    assert poster.filename.startswith(f"{VIDEO_ID}-maxresdefault")
    assert VideoBlock().clean(video_value(poster=poster))["poster"] == poster


@responses.activate
def test_changing_the_video_replaces_its_thumbnail():
    old_thumbnail = stored_image(f"{OTHER_VIDEO_ID}-maxresdefault.jpg")
    mock_thumbnail(MAXRES_URL)

    poster = VideoBlock().clean(video_value(poster=old_thumbnail))["poster"]

    assert poster.filename.startswith(f"{VIDEO_ID}-maxresdefault")


@responses.activate
def test_editor_image_with_youtube_thumbnail_selected_is_rejected(editor_poster):
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(poster=editor_poster))

    assert list(block_errors(exc_info)) == ["poster"]
    assert len(responses.calls) == 0


@responses.activate
def test_youtube_thumbnail_rejected_for_self_hosted_video():
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(video_url=SELF_HOSTED_URL))

    assert list(block_errors(exc_info)) == ["poster_source"]
    assert len(responses.calls) == 0


@responses.activate
def test_youtube_thumbnail_needs_a_link_to_a_video():
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(video_url="https://www.youtube.com/@firefox"))

    assert list(block_errors(exc_info)) == ["video_url"]


@responses.activate
def test_youtube_unreachable_reports_on_the_poster_after_one_attempt():
    responses.add(responses.GET, MAXRES_URL, body=requests.ConnectionError("down"))

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value())

    assert "Couldn't reach YouTube" in block_errors(exc_info)["poster"][0]
    assert [call.request.url for call in responses.calls] == [MAXRES_URL]


@responses.activate
def test_video_without_youtube_thumbnail_asks_for_an_upload():
    responses.add(responses.GET, MAXRES_URL, status=404)
    responses.add(responses.GET, HQ_URL, status=404)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value())

    assert "Upload an image" in block_errors(exc_info)["poster"][0]


@responses.activate
def test_thumbnail_downloads_stop_when_the_request_is_out_of_time(admin_request):
    setattr(admin_request, YOUTUBE_THUMBNAIL_DEADLINE_ATTR, time.monotonic() - 1)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value())

    assert "Save again" in block_errors(exc_info)["poster"][0]
    assert len(responses.calls) == 0


@pytest.fixture
def clock():
    now = [0.0]
    with mock.patch("springfield.cms.blocks.time.monotonic", side_effect=lambda: now[0]):
        yield now


@responses.activate
def test_fallback_is_skipped_when_the_first_attempt_used_up_the_time(admin_request, clock):
    def slow_not_found(request):
        clock[0] = 11
        return 404, {}, ""

    responses.add_callback(responses.GET, MAXRES_URL, callback=slow_not_found)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value())

    assert "Save again" in block_errors(exc_info)["poster"][0]
    assert [call.request.url for call in responses.calls] == [MAXRES_URL]


@responses.activate
def test_download_stops_when_the_body_runs_past_the_time(admin_request, clock):
    def slow_body(request):
        clock[0] = 11
        return 200, {"Content-Type": "image/jpeg"}, jpeg((255, 0, 0))

    responses.add_callback(responses.GET, MAXRES_URL, callback=slow_body)

    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value())

    assert "Save again" in block_errors(exc_info)["poster"][0]
    assert not SpringfieldImage.objects.filter(title__startswith="YouTube thumbnail").exists()


@responses.activate
def test_storage_failure_reports_on_the_poster():
    mock_thumbnail(MAXRES_URL)

    with mock.patch.object(SpringfieldImage.objects, "create", side_effect=OSError("storage down")):
        with pytest.raises(StructBlockValidationError) as exc_info:
            VideoBlock().clean(video_value())

    assert "Couldn't save" in block_errors(exc_info)["poster"][0]


@responses.activate
def test_preview_does_not_download(preview_request):
    old_thumbnail = stored_image(f"{OTHER_VIDEO_ID}-maxresdefault.jpg")

    value = VideoBlock().clean(video_value(poster=old_thumbnail))

    assert value["poster"] is None
    assert len(responses.calls) == 0


@responses.activate
def test_draft_saves_without_poster_when_youtube_has_none():
    responses.add(responses.GET, MAXRES_URL, status=404)
    responses.add(responses.GET, HQ_URL, status=404)

    value = VideoBlock().clean_deferred(video_value())

    assert value["poster"] is None


@pytest.mark.parametrize(
    "data",
    [
        video_data(video_url="", alt=""),
        video_data(video_url=SELF_HOSTED_URL, poster_source=POSTER_SOURCE_UPLOAD),
        video_data(video_url=SELF_HOSTED_URL),
        video_data(poster_source=POSTER_SOURCE_UPLOAD),
    ],
)
def test_draft_saves_with_incomplete_video(data):
    value = VideoBlock().clean_deferred(VideoBlock().to_python(data))

    assert value["poster"] is None


@responses.activate
def test_draft_keeps_editor_image_with_youtube_thumbnail_selected(editor_poster):
    value = VideoBlock().clean_deferred(video_value(poster=editor_poster))

    assert value["poster"] == editor_poster
    assert len(responses.calls) == 0


@pytest.mark.parametrize(
    "video_url, message",
    [
        (SELF_HOSTED_URL, "Videos from assets.mozilla.net need one."),
        (YOUTUBE_URL, "Choose a poster image, or set Poster to 'YouTube thumbnail'."),
    ],
)
def test_publish_requires_an_uploaded_poster(video_url, message):
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(video_url=video_url, poster_source=POSTER_SOURCE_UPLOAD))

    assert message in block_errors(exc_info)["poster"][0]


def test_publish_reports_missing_poster_with_other_errors():
    with pytest.raises(StructBlockValidationError) as exc_info:
        VideoBlock().clean(video_value(video_url=SELF_HOSTED_URL, poster_source=POSTER_SOURCE_UPLOAD, alt=""))

    assert set(block_errors(exc_info)) == {"alt", "poster"}


@responses.activate
def test_uploaded_poster_is_kept(editor_poster):
    value = VideoBlock().clean(video_value(poster_source=POSTER_SOURCE_UPLOAD, poster=editor_poster))

    assert value["poster"] == editor_poster
    assert len(responses.calls) == 0


@responses.activate
def test_blog_hero_video_gets_youtube_thumbnail():
    mock_thumbnail(MAXRES_URL)
    stream_block = BlogArticlePage._meta.get_field("hero_video").stream_block

    value = stream_block.clean(stream_block.to_python([{"type": "video", "value": video_data()}]))

    assert value[0].value["poster"].filename.startswith(f"{VIDEO_ID}-maxresdefault")


def test_blog_hero_video_requires_poster_for_self_hosted_video():
    stream_block = BlogArticlePage._meta.get_field("hero_video").stream_block
    data = video_data(video_url=SELF_HOSTED_URL, poster_source=POSTER_SOURCE_UPLOAD)

    with pytest.raises(StreamBlockValidationError):
        stream_block.clean(stream_block.to_python([{"type": "video", "value": data}]))


@pytest.mark.parametrize("video_url", [YOUTUBE_URL, SELF_HOSTED_URL, f"https://www.youtube.com/shorts/{VIDEO_ID}"])
def test_render_with_poster(video_url, editor_poster):
    data = video_data(video_url=video_url, poster_source=POSTER_SOURCE_UPLOAD, poster=editor_poster)

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
