# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from wagtail_localize.models import String, StringSegment, StringTranslation
from wagtail_localize.strings import StringValue


def set_rich_text(translated_page, html):
    """Replace the source page's rich text and re-extract its segments, which is what
    an editor's save does."""
    translated_page.source_page.content = html
    translated_page.source_page.save()
    translated_page.translation.source.update_from_db()
    translated_page.translation.source.refresh_segments()


def content_context(translated_page):
    """The context of the rich text field, which holds one segment per paragraph."""
    return StringSegment.objects.filter(source=translated_page.translation.source, context__path="content").first().context


def title_context(translated_page):
    """The context of the title, which holds a single segment."""
    return StringSegment.objects.get(source=translated_page.translation.source, context__path="title").context


def orphan_stringtranslation(translated_page, context, source_text, value, **kwargs):
    """
    A StringTranslation at `context` whose source String has no segment there.

    This is the state wagtail-localize leaves behind when an editor changes the
    source: refresh_segments() drops the StringSegment and leaves the translation.
    """
    string = String.from_value(translated_page.translation.source.locale, StringValue(source_text))
    defaults = {
        "data": value,
        "translation_type": StringTranslation.TRANSLATION_TYPE_MANUAL,
        "tool_name": "",
        "has_error": False,
    }
    defaults.update(kwargs)
    return StringTranslation.objects.create(
        translation_of=string,
        locale=translated_page.locale,
        context=context,
        **defaults,
    )
