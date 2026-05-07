# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uuid

from bs4 import BeautifulSoup
from wagtail.blocks import RichTextBlock as WagtailRichTextBlock
from wagtail.fields import RichTextField as WagtailRichTextField


def inject_link_uids(html):
    """Add a uid attribute to any <a> tag in raw rich text HTML that lacks one."""
    if not html:
        return html
    soup = BeautifulSoup(html, "html.parser")
    changed = False
    for a_tag in soup.find_all("a"):
        if not a_tag.get("uid"):
            a_tag["uid"] = str(uuid.uuid4())
            changed = True
    return str(soup) if changed else html


class RichTextBlock(WagtailRichTextBlock):
    def get_prep_value(self, value):
        return inject_link_uids(super().get_prep_value(value))


class RichTextField(WagtailRichTextField):
    def pre_save(self, model_instance, add):
        value = super().pre_save(model_instance, add)
        if value:
            injected = inject_link_uids(value)
            if injected != value:
                setattr(model_instance, self.attname, injected)
                return injected
        return value
