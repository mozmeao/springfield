# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.urls import path

from wagtail import hooks

from springfield.blog.admin_views import blog_tag_autocomplete


@hooks.register("register_admin_urls")
def register_cms_admin_urls():
    return [
        path("blog-tag-autocomplete/", blog_tag_autocomplete, name="blog_tag_autocomplete"),
    ]
