# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.test import RequestFactory, override_settings

from springfield.utils import views


def test_variation_template_view():
    rf = RequestFactory()
    view = views.VariationTemplateView(template_context_variations=["b"], template_name_variations=["b", "c"], template_name="base/book.html")
    req = rf.get("/", data={"v": "b"})
    view.request = req
    assert view.get_context_data()["variation"] == "b"
    assert view.get_template_names() == ["base/book-b.html"]

    req = rf.get("/", data={"v": "dude"})
    view.request = req
    assert view.get_context_data()["variation"] == ""
    assert view.get_template_names() == ["base/book.html"]

    req = rf.get("/", data={"v": "c"})
    view.request = req
    assert view.get_context_data()["variation"] == ""
    assert view.get_template_names() == ["base/book-c.html"]

    view = views.VariationTemplateView(template_name_variations=["1"], template_name="about.index.html")
    req = rf.get("/", data={"v": "1"})
    view.request = req
    assert "variation" not in view.get_context_data()
    assert view.get_template_names() == ["about.index-1.html"]


@override_settings(LANG_GROUPS={"en": ["en-US", "en-GB"]})
def test_variation_template_view_locales():
    rf = RequestFactory()
    view = views.VariationTemplateView(
        template_context_variations=["b"], template_name_variations=["b", "c"], template_name="base/book.html", variation_locales=["de", "fr", "en"]
    )
    req = rf.get("/", data={"v": "b"})
    req.locale = "fr"
    view.request = req
    assert view.get_context_data()["variation"] == "b"
    assert view.get_template_names() == ["base/book-b.html"]

    # locale groups
    req = rf.get("/", data={"v": "b"})
    req.locale = "en-GB"
    view.request = req
    assert view.get_context_data()["variation"] == "b"
    assert view.get_template_names() == ["base/book-b.html"]

    req = rf.get("/", data={"v": "b"})
    req.locale = "pt-BR"
    view.request = req
    assert view.get_context_data()["variation"] == ""
    assert view.get_template_names() == ["base/book.html"]

    req = rf.get("/", data={"v": "c"})
    req.locale = "de"
    view.request = req
    assert view.get_context_data()["variation"] == ""
    assert view.get_template_names() == ["base/book-c.html"]
