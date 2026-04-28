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
_COLLIDING_PATHS = frozenset(
    {
        "mobile-24/add/add-24",
        "mobile-24/app-menu-more-options/app-menu-space-24",
        "mobile-24/arrows-chevrons/arrow-clockwise-24",
        "mobile-24/arrows-chevrons/arrow-trending-24",
        "mobile-24/arrows-chevrons/back-24",
        "mobile-24/bookmark/bookmark-24",
        "mobile-24/bookmark/bookmark-fill-24",
        "mobile-24/checkmark/checkmark-24",
        "mobile-24/arrows-chevrons/chevron-down-24",
        "mobile-24/arrows-chevrons/chevron-left-24",
        "mobile-24/arrows-chevrons/chevron-right-24",
        "mobile-24/arrows-chevrons/chevron-up-24",
        "mobile-24/alerts-info-help/critical-fill-24",
        "mobile-24/data-clearance/data-clearance-24",
        "mobile-24/delete/delete-24",
        "mobile-24/devices/device-mobile-24",
        "mobile-24/mail/email-shield-24",
        "mobile-24/experiments/experiments-24",
        "mobile-24/extensions/extension-critical-24",
        "mobile-24/extensions/extension-fill-24",
        "mobile-24/extensions/extension-warning-24",
        "mobile-24/external-link/external-link-24",
        "mobile-24/search/find-in-page-24",
        "mobile-24/arrows-chevrons/forward-24",
        "mobile-24/globe/globe-24",
        "mobile-24/history/history-24",
        "mobile-24/home/home-24",
        "mobile-24/alerts-info-help/information-24",
        "mobile-24/alerts-info-help/information-fill-24",
        "mobile-24/lightbulb/lightbulb-24",
        "mobile-24/lock/lock-24",
        "mobile-24/lock/lock-warning-24",
        "mobile-24/permissions/login-24",
        "mobile-24/shopping/packaging-24",
        "mobile-24/passkey/passkey-24",
        "mobile-24/pin/pin-24",
        "mobile-24/pin/pin-fill-24",
        "mobile-24/shopping/price-24",
        "mobile-24/print/print-24",
        "mobile-24/private-mode/private-mode-circle-fill-24",
        "mobile-24/shopping/quality-24",
        "mobile-24/search/search-24",
        "mobile-24/shield/shield-24",
        "mobile-24/shopping/shipping-24",
        "mobile-24/shopping/shopping-24",
        "mobile-24/edit-copy-paste/signature-properties-24",
        "mobile-24/sort/sort-24",
        "mobile-24/subtract/subtract-24",
        "mobile-24/sync/sync-24",
        "mobile-24/tabs/tab-24",
        "mobile-24/themes/themes-24",
        "mobile-24/translate/translate-24",
        "mobile-24/alerts-info-help/warning-24",
        "mobile-24/alerts-info-help/warning-fill-24",
    }
)


def icon_value_fn(rel_path: str) -> str:
    """Convert a ThumbnailChoiceBlock directory-relative path to a stored value.

    Called by ThumbnailChoiceBlock with the file's path relative to thumbnail_directory,
    without extension (e.g. "desktop-16/arrows-and-chevrons/forward-16").

    Returns the CSS logical name, stripping both directory prefix and size suffix:

        "desktop-16/arrows-and-chevrons/forward-16" -> "forward"
        "desktop-16/permissions/auto-play-false"    -> "auto-play-false"
        "desktop-16/screenshot/screenshot-camera-16"-> "screenshot-camera"

    Exception: icons in _COLLIDING_PATHS return their relative path unchanged
    to preserve uniqueness when two files would otherwise produce the same CSS name.
    """
    if rel_path in _COLLIDING_PATHS:
        return rel_path
    return icon_css_name(rel_path.split("/")[-1])
