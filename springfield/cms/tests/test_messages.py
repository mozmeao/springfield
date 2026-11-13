# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import messages
from django.test import RequestFactory
from django.utils.safestring import mark_safe

import pytest
from wagtail_localize_smartling.locks import PendingTranslationLock

from springfield.cms.messages import SpringfieldCookieStorage


def make_storage():
    return SpringfieldCookieStorage(RequestFactory().get("/cms-admin/"))


def pending_translation_banner():
    return mark_safe(f'<span class="{PendingTranslationLock.message_class}"><b>This page is being translated.</b></span>')


MESSAGE_LEVELS = [messages.INFO, messages.SUCCESS, messages.WARNING, messages.ERROR]


@pytest.mark.parametrize(
    "original_level,expected_level",
    [
        (messages.INFO, messages.WARNING),
        (messages.SUCCESS, messages.SUCCESS),
        (messages.WARNING, messages.WARNING),
        (messages.ERROR, messages.ERROR),
    ],
    ids=["info", "success", "warning", "error"],
)
def test_pending_translation_banner_levels(original_level, expected_level):
    """Only INFO PendingTranslationLock messages are changed to WARNING messages."""
    storage = make_storage()

    storage.add(original_level, pending_translation_banner(), extra_tags="lock")

    assert [message.level for message in storage] == [expected_level]


@pytest.mark.parametrize("level", MESSAGE_LEVELS)
def test_another_lock_banner_keeps_its_level(level):
    """A banner that is not a PendingTranslationLock's keeps its message level."""
    storage = make_storage()

    storage.add(level, mark_safe("<b>Page 'Home' is locked</b>"), extra_tags="lock")

    assert [message.level for message in storage] == [level]


@pytest.mark.parametrize("level", MESSAGE_LEVELS)
def test_a_message_that_is_not_a_lock_banner_keeps_its_level(level):
    storage = make_storage()

    storage.add(level, pending_translation_banner())

    assert [message.level for message in storage] == [level]
