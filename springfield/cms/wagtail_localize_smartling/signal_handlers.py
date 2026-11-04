# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Receivers for signals sent by
# github.com/mozilla/wagtail-localize-smartling/

import logging

from django.dispatch import receiver

from sentry_sdk import capture_exception
from wagtail_localize_smartling.signals import job_sync_failed

logger = logging.getLogger(__name__)


@receiver(job_sync_failed)
def report_sync_failure(sender, instance, exception, permanent, **kwargs):
    """Report a Smartling job that has stopped being retried."""
    if not permanent:
        logger.warning("Smartling job %s failed to sync and will be retried", instance.pk)
        return

    try:
        capture_exception(exception)
    except Exception:
        # Reporting is not worth failing a sync run over.
        logger.exception("Could not report blocked Smartling job %s", instance.pk)
