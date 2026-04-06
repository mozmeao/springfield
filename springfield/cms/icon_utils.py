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
