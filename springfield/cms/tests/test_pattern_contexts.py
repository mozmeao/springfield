# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from springfield.cms.pattern_contexts import add_icon_groups


def test_add_icon_groups_lists_icons_by_folder():
    context = {}
    add_icon_groups(context=context, request=None)

    groups = {group["title"]: group["icons"] for group in context["icon_groups"]}
    assert {"name": "Globe", "icon_name": "globe"} in groups["Desktop 16"]
    assert {"name": "Toggle On", "icon_name": "toggle-on"} in groups["Other"]
