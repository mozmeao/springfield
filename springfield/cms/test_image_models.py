# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import BytesIO
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

import pytest
from bs4 import BeautifulSoup
from markupsafe import escape
from PIL import Image as PillowImage
from wagtail.images.forms import get_image_form
from wagtail.images.jinja2tags import image as render_image, srcset_image as render_srcset_image

from springfield.cms.fields import SanitizingWagtailImageField
from springfield.cms.models.images import SpringfieldImage, _make_renditions

pytestmark = [pytest.mark.django_db]


class SpringfieldImageTestCase(TestCase):
    @override_settings(TASK_QUEUE_AVAILABLE=False)
    def test_pre_generate_expected_renditions__no_queue_available(self):
        image = SpringfieldImage(width=1, height=1)
        expected_filter_specs = [
            "width-2400",
            "width-2200",
            "width-2000",
            "width-1800",
            "width-1600",
            "width-1400",
            "width-1200",
            "width-1000",
            "width-800",
            "width-600",
            "width-400",
            "width-200",
            "width-100",
            "max-165x165",
        ]

        with patch("springfield.cms.models.images._make_renditions") as _make_renditions_mock:
            image._pre_generate_expected_renditions()
            _make_renditions_mock.assert_called_once_with(image_id=image.id, filter_specs=expected_filter_specs)

    @override_settings(TASK_QUEUE_AVAILABLE=True)
    def test_pre_generate_expected_renditions__queue_available(self):
        image = SpringfieldImage(width=1, height=1)
        expected_filter_specs = [
            "width-2400",
            "width-2200",
            "width-2000",
            "width-1800",
            "width-1600",
            "width-1400",
            "width-1200",
            "width-1000",
            "width-800",
            "width-600",
            "width-400",
            "width-200",
            "width-100",
            "max-165x165",
        ]

        with patch("springfield.base.tasks.django_rq") as mock_django_rq:
            mock_queue = Mock(name="mocked_queue")
            mock_django_rq.get_queue.return_value = mock_queue

            image._pre_generate_expected_renditions()

            mock_django_rq.get_queue.assert_called_once_with("image_renditions")
            mock_queue.enqueue.assert_called_once_with(
                _make_renditions,
                image_id=image.id,
                filter_specs=expected_filter_specs,
            )

    def test_pre_generate_expected_renditions_uses_defer_task(self):
        image = SpringfieldImage(width=1, height=1)
        expected_filter_specs = [
            "width-2400",
            "width-2200",
            "width-2000",
            "width-1800",
            "width-1600",
            "width-1400",
            "width-1200",
            "width-1000",
            "width-800",
            "width-600",
            "width-400",
            "width-200",
            "width-100",
            "max-165x165",
        ]
        with patch("springfield.cms.models.images.defer_task") as mock_defer_task:
            image._pre_generate_expected_renditions()
            mock_defer_task.assert_called_once_with(
                _make_renditions,
                queue_name="image_renditions",
                func_kwargs={
                    "image_id": image.id,
                    "filter_specs": expected_filter_specs,
                },
            )

    def test_pre_generate_expected_renditions_called_on_save(self):
        image = SpringfieldImage(width=1, height=1)
        with patch.object(image, "_pre_generate_expected_renditions") as pre_generate_mock:
            image.save()
            pre_generate_mock.assert_called_once_with()

    def test_springfield_image_uses_sanitizing_field(self):
        """Verify that SpringfieldImage forms use SanitizingWagtailImageField."""

        ImageForm = get_image_form(SpringfieldImage)
        form = ImageForm()

        # Check that the 'file' field is our custom sanitizing field
        self.assertIsInstance(
            form.fields["file"],
            SanitizingWagtailImageField,
        )


def test_image_form_does_not_fill_the_title_from_the_file_name():
    form = get_image_form(SpringfieldImage)()

    file_attrs = form.fields["file"].widget.attrs

    assert "data-controller" not in file_attrs
    assert form.fields["title"].required
    assert not form["title"].value()


@pytest.fixture
def make_image():
    """Build one saved SpringfieldImage, with the rendition pre-generation stubbed out."""

    def build(**fields):
        buffer = BytesIO()
        PillowImage.new("RGB", (400, 300), (117, 79, 224)).save(buffer, format="PNG")
        buffer.seek(0)
        with patch.object(SpringfieldImage, "_pre_generate_expected_renditions"):
            return SpringfieldImage.objects.create(
                file=ContentFile(buffer.read(), "placeholder.png"),
                **{"title": "Firefox logo", "description": "The Firefox logo", **fields},
            )

    return build


def find_img(rendered):
    """The <img> element a tag's return value produces, rendered the way Jinja renders it."""
    return BeautifulSoup(str(escape(rendered)), "html.parser").find("img")


def test_decorative_image_renders_no_alt_attribute(make_image):
    decorative_image = make_image(is_decorative=True)

    srcset_tag = find_img(render_srcset_image(decorative_image, "width-{200,400}"))
    assert srcset_tag.has_attr("srcset")
    assert not srcset_tag.has_attr("alt")

    assert not find_img(render_image(decorative_image, "width-400")).has_attr("alt")


def test_image_renders_alt_from_its_description(make_image):
    described_image = make_image()

    assert find_img(render_srcset_image(described_image, "width-{200,400}"))["alt"] == "The Firefox logo"
    assert find_img(render_image(described_image, "width-400"))["alt"] == "The Firefox logo"


def test_alt_passed_by_a_template_wins_over_the_decorative_flag(make_image):
    decorative_image = make_image(is_decorative=True)

    rendered = render_image(decorative_image, "width-400", alt="Chosen for this one use")

    assert find_img(rendered)["alt"] == "Chosen for this one use"


@pytest.mark.parametrize(
    "title",
    [
        "fx_blog_header_extensions_writing",
        "Monitor-1000x542.jpg",
        "Disconnect-Study-Blog-Post-Graph-01-1-300x150",
        "hero.png",
        "  hero.png  ",
        "firefox-enterprise",
    ],
)
def test_full_clean_rejects_titles_that_name_a_file(title):
    unsaved_image = SpringfieldImage(title=title, description="The Firefox logo", width=1, height=1)

    with pytest.raises(ValidationError) as raised:
        unsaved_image.full_clean(exclude=["file"])

    assert "title" in raised.value.error_dict


@pytest.mark.parametrize(
    "title",
    [
        "Firefox logo",
        "A menu button in Firefox",
        "Firefox",
        "Monitor 1000x542",
    ],
)
def test_full_clean_accepts_titles_that_describe_the_image(title):
    unsaved_image = SpringfieldImage(title=title, description="The Firefox logo", width=1, height=1)

    unsaved_image.full_clean(exclude=["file"])


def test_decorative_image_needs_no_description():
    unsaved_image = SpringfieldImage(title="A decorative image", is_decorative=True, width=1, height=1)

    unsaved_image.full_clean(exclude=["file"])


def test_non_decorative_image_requires_description():
    unsaved_image = SpringfieldImage(title="Not a decorative image", width=1, height=1)
    with pytest.raises(ValidationError) as raised:
        unsaved_image.full_clean(exclude=["file"])

    assert "description" in raised.value.error_dict
