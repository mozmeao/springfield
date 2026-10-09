# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from springfield.cms.images.forms import InlineImageForm

pytestmark = [pytest.mark.django_db]


def test_inline_form_fields_point_at_the_row_form(make_image):
    image = make_image()

    form = InlineImageForm(instance=image)

    assert list(form.fields) == ["title", "description", "is_decorative", "tags"]
    assert form.form_id == f"image-inline-{image.pk}"
    assert form["title"].html_name == f"image-{image.pk}-title"
    assert all(field.widget.attrs["form"] == form.form_id for field in form.fields.values())
    assert 'data-controller="w-tag"' in str(form["tags"])


def test_inline_form_saves_the_four_fields(make_image):
    image = make_image()
    prefix = f"image-{image.pk}"

    form = InlineImageForm(
        {
            f"{prefix}-title": "Firefox logo on purple",
            f"{prefix}-description": "The Firefox logo on a purple background",
            f"{prefix}-is_decorative": "on",
            f"{prefix}-tags": "brand, logo",
        },
        instance=image,
    )

    assert form.is_valid(), form.errors
    form.save()
    image.refresh_from_db()
    assert image.title == "Firefox logo on purple"
    assert image.description == "The Firefox logo on a purple background"
    assert image.is_decorative is True
    assert set(image.tags.names()) == {"brand", "logo"}


def test_inline_form_applies_the_image_model_validation(make_image):
    image = make_image()
    prefix = f"image-{image.pk}"

    form = InlineImageForm(
        {f"{prefix}-title": "firefox_logo.png", f"{prefix}-description": "", f"{prefix}-tags": ""},
        instance=image,
    )

    assert not form.is_valid()
    assert set(form.errors) == {"title", "description"}
