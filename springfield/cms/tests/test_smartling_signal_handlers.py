# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

import pytest
from wagtail_localize_smartling.signals import job_sync_failed

from springfield.cms.tests.factories import SimpleRichTextPageFactory, create_smartling_job


@pytest.mark.django_db
@mock.patch("springfield.cms.wagtail_localize_smartling.signal_handlers.capture_exception")
def test_a_permanent_failure_is_reported(mock_capture_exception):
    job = create_smartling_job([SimpleRichTextPageFactory()])
    error = ValueError("duplicate job name")

    job_sync_failed.send(sender=type(job), instance=job, exception=error, permanent=True)

    mock_capture_exception.assert_called_once_with(error)


@pytest.mark.django_db
@mock.patch("springfield.cms.wagtail_localize_smartling.signal_handlers.capture_exception")
def test_a_transient_failure_is_not_reported(mock_capture_exception):
    """It is retried every few minutes and usually resolves on its own."""
    job = create_smartling_job([SimpleRichTextPageFactory()])

    job_sync_failed.send(sender=type(job), instance=job, exception=TimeoutError(), permanent=False)

    mock_capture_exception.assert_not_called()


@pytest.mark.django_db
@mock.patch("springfield.cms.wagtail_localize_smartling.signal_handlers.capture_exception")
def test_a_failure_to_report_is_swallowed(mock_capture_exception):
    """Asserts by not raising: an outage at the reporting end is not the sync's problem."""
    mock_capture_exception.side_effect = RuntimeError("sentry is down")
    job = create_smartling_job([SimpleRichTextPageFactory()])

    job_sync_failed.send(sender=type(job), instance=job, exception=ValueError(), permanent=True)
