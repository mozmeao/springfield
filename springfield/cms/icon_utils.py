# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re

_SIZE_SUFFIX_RE = re.compile(r"-\d+$")


def icon_css_name(stem):
    """Strip trailing size suffix from an icon filename stem.

    'activity-16'        → 'activity'
    'arrow-clockwise-16' → 'arrow-clockwise'
    'add-circle-fill-16' → 'add-circle-fill'
    """
    return _SIZE_SUFFIX_RE.sub("", stem)


# some icon paths produce the same CSS name as another icon.
# For these specific files, icon_value_fn returns the relative path instead of
# the CSS name to avoid the collision.
_COLLIDING_PATHS = frozenset()


def icon_value_fn(rel_path: str) -> str:
    """Convert a ThumbnailChoiceBlock directory-relative path to a stored value.

    Called by ThumbnailChoiceBlock with the file's path relative to thumbnail_directory,
    without extension (e.g. "desktop-16/arrows-and-chevrons/forward-16").

    Returns the CSS logical name, stripping both directory prefix and size suffix:

        "desktop-16/arrows-and-chevrons/forward-16" -> "forward"
        "desktop-16/permissions/auto-play-false"    -> "auto-play-false"
        "desktop-16/screenshot/screenshot-camera-16"-> "screenshot-camera"

    Exception: icons in _COLLIDING_PATHS return their relative path with "/" replaced
    by "-" to produce a unique, CSS-safe name without path separators:

        "mobile-24/arrows-chevrons/forward-24" -> "mobile-24-arrows-chevrons-forward-24"
    """
    if rel_path in _COLLIDING_PATHS:
        return rel_path.replace("/", "-")
    return icon_css_name(rel_path.split("/")[-1])
