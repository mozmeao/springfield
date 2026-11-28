# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# No model imports: the data migration imports the pure functions from here.

from wagtail.search import index as search_index

RATIOS = ((16, 9), (9, 16), (4, 3), (3, 4), (3, 2), (2, 3), (1, 1))
RATIO_TAG_NAMES = frozenset(f"{ratio_width}:{ratio_height}" for ratio_width, ratio_height in RATIOS)

NEAR_TOLERANCE = 0.1


def get_exact_ratio_tag(width: int, height: int) -> str | None:
    """Return the ratio tag whose proportions the pixel size matches, allowing for rounding."""
    if width <= 0 or height <= 0:
        return None
    for ratio_width, ratio_height in RATIOS:
        if abs(height - width * ratio_height / ratio_width) <= 1:
            return f"{ratio_width}:{ratio_height}"
    return None


def get_near_ratio_tag(width: int, height: int) -> str | None:
    """Return the closest ratio tag within NEAR_TOLERANCE of the pixel size, or None when it is
    exact or not near. Neighbouring ratios such as 4:3 and 3:2 are closer together than twice the
    tolerance, so an image can be near both."""
    if width <= 0 or height <= 0 or get_exact_ratio_tag(width, height):
        return None
    deviation, tag = min(
        (abs(width / height - ratio_width / ratio_height) / (ratio_width / ratio_height), f"{ratio_width}:{ratio_height}")
        for ratio_width, ratio_height in RATIOS
    )
    return tag if deviation <= NEAR_TOLERANCE else None


def apply_ratio_tags(image) -> None:
    """Replace the image's ratio tags with its exact one, if any, then refresh its search index."""
    image.tags.remove(*RATIO_TAG_NAMES)
    exact_tag = get_exact_ratio_tag(image.width, image.height)
    if exact_tag:
        image.tags.add(exact_tag)
    search_index.insert_or_update_object(image)
