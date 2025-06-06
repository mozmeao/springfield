# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch

from qrcode.image.svg import SvgPathFillImage

from springfield.base.templatetags.qrcode import qrcode
from springfield.base.tests import TestCase


@patch("springfield.base.templatetags.qrcode.cache")
@patch("springfield.base.templatetags.qrcode.qr")
class TestQRCode(TestCase):
    def test_qrcode_cache_cold(self, qr_mock, cache_mock):
        cache_mock.get.return_value = None
        data = "https://dude.abide"
        qrcode(data, 20)
        qr_mock.make.assert_called_with(data, image_factory=SvgPathFillImage, box_size=20)

    def test_qrcode_cache_warm(self, qr_mock, cache_mock):
        cache_mock.get.return_value = "<svg>stuff</svg>"
        data = "https://dude.abide"
        qrcode(data, 20)
        qr_mock.make.assert_not_called()
