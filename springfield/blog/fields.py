# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from modelcluster.contrib.taggit import ClusterTaggableManager

from springfield.blog.forms import LocaleTagField


class LocalizedClusterTaggableManager(ClusterTaggableManager):
    """A ClusterTaggableManager whose form field resolves tags within one locale.

    Wagtail's default form field for a TaggableManager is name-based and locale-blind; see
    springfield.blog.forms.LocaleTagField for what replaces it.
    """

    def formfield(self, form_class=None, **kwargs):
        return super().formfield(form_class=LocaleTagField, **kwargs)
