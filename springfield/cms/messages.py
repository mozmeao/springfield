# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from django.contrib.messages import constants
from django.contrib.messages.storage.cookie import CookieStorage

from wagtail_localize_smartling.locks import PendingTranslationLock


class SpringfieldCookieStorage(CookieStorage):
    def add(self, level, message, extra_tags=""):
        """
        Set "lock" messages to the WARNING level.

        Wagtail sets a message's level by whether the lock stops the viewer.
        As a result, a superuser who may edit a page may receive an 'info' warning.
        The message level is chosen inline in the page editor, with no hook of
        its own, so instead, we set the the level to WARNING here for all
        messages with "lock" extra tags.
        """
        if level == constants.INFO and extra_tags == "lock" and PendingTranslationLock.message_class in str(message):
            level = constants.WARNING
        super().add(level, message, extra_tags)
