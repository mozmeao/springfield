# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import pytest

from springfield.cms.images.ratios import apply_ratio_tags, get_exact_ratio_tag, get_near_ratio_tag


@pytest.mark.parametrize(
    ("width", "height", "expected"),
    [
        (1920, 1080, "16:9"),
        (1366, 768, "16:9"),  # 768.375, rounding
        (1080, 1920, "9:16"),
        (1600, 1200, "4:3"),
        (1200, 1600, "3:4"),
        (1500, 1000, "3:2"),
        (1000, 1500, "2:3"),
        (500, 500, "1:1"),
        (1366, 769, "16:9"),  # 0.625px off, within 1px
        (1366, 770, None),  # 1.625px off
        (1920, 1082, None),  # 2px off is not exact
        (1000, 300, None),
        (0, 0, None),
        (100, 0, None),
    ],
)
def test_get_exact_ratio_tag(width, height, expected):
    assert get_exact_ratio_tag(width, height) == expected


@pytest.mark.parametrize(
    ("width", "height", "expected"),
    [
        (1920, 1050, "16:9"),
        (1050, 1920, "9:16"),
        (1920, 985, "16:9"),  # just inside 10%
        (1920, 975, None),  # just outside 10%
        (1450, 1000, "3:2"),  # near both 4:3 and 3:2, closer to 3:2
        (1000, 1450, "2:3"),  # near both 3:4 and 2:3, closer to 2:3
        (1920, 1080, None),  # exact, not near
        (1000, 300, None),
        (0, 0, None),
    ],
)
def test_get_near_ratio_tag(width, height, expected):
    assert get_near_ratio_tag(width, height) == expected


@pytest.mark.django_db
def test_apply_ratio_tags_replaces_stale_ratio_tags_and_keeps_others(make_image):
    image = make_image()  # 400×300 → 4:3
    image.tags.add("16:9", "brand")
    apply_ratio_tags(image)
    assert sorted(image.tags.names()) == ["4:3", "brand"]


@pytest.mark.django_db
def test_apply_ratio_tags_removes_ratio_tags_when_nothing_matches(make_image):
    image = make_image()
    # Set in memory only: apply_ratio_tags reads the size from the instance, not the DB.
    image.width, image.height = 1000, 300
    image.tags.add("4:3")
    apply_ratio_tags(image)
    assert list(image.tags.names()) == []
