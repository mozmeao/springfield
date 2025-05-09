# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

import pytest

from springfield.cms.models.images import SpringfieldImage, _make_renditions

pytestmark = [pytest.mark.django_db]


class SpringfieldImageTestCase(TestCase):
    @override_settings(TASK_QUEUE_AVAILABLE=False)
    def test_pre_generate_expected_renditions__no_queue_available(self):
        image = SpringfieldImage(width=1, height=1)
        expected_filter_specs = [
            "width-2400",
            "width-2200",
            "width-2000",
            "width-1800",
            "width-1600",
            "width-1400",
            "width-1200",
            "width-1000",
            "width-800",
            "width-600",
            "width-400",
            "width-200",
            "width-100",
            "max-165x165",
        ]

        with patch("springfield.cms.models.images._make_renditions") as _make_renditions_mock:
            image._pre_generate_expected_renditions()
            _make_renditions_mock.assert_called_once_with(image_id=image.id, filter_specs=expected_filter_specs)

    @override_settings(TASK_QUEUE_AVAILABLE=True)
    def test_pre_generate_expected_renditions__queue_available(self):
        image = SpringfieldImage(width=1, height=1)
        expected_filter_specs = [
            "width-2400",
            "width-2200",
            "width-2000",
            "width-1800",
            "width-1600",
            "width-1400",
            "width-1200",
            "width-1000",
            "width-800",
            "width-600",
            "width-400",
            "width-200",
            "width-100",
            "max-165x165",
        ]

        with patch("springfield.base.tasks.django_rq") as mock_django_rq:
            mock_queue = Mock(name="mocked_queue")
            mock_django_rq.get_queue.return_value = mock_queue

            image._pre_generate_expected_renditions()

            mock_django_rq.get_queue.assert_called_once_with("image_renditions")
            mock_queue.enqueue.assert_called_once_with(
                _make_renditions,
                image_id=image.id,
                filter_specs=expected_filter_specs,
            )

    def test_pre_generate_expected_renditions_uses_defer_task(self):
        image = SpringfieldImage(width=1, height=1)
        expected_filter_specs = [
            "width-2400",
            "width-2200",
            "width-2000",
            "width-1800",
            "width-1600",
            "width-1400",
            "width-1200",
            "width-1000",
            "width-800",
            "width-600",
            "width-400",
            "width-200",
            "width-100",
            "max-165x165",
        ]
        with patch("springfield.cms.models.images.defer_task") as mock_defer_task:
            image._pre_generate_expected_renditions()
            mock_defer_task.assert_called_once_with(
                _make_renditions,
                queue_name="image_renditions",
                func_kwargs={
                    "image_id": image.id,
                    "filter_specs": expected_filter_specs,
                },
            )

    def test_pre_generate_expected_renditions_called_on_save(self):
        image = SpringfieldImage(width=1, height=1)
        with patch.object(image, "_pre_generate_expected_renditions") as pre_generate_mock:
            image.save()
            pre_generate_mock.assert_called_once_with()
