# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest.mock import patch

from qrcode.image.svg import SvgPathFillImage

from springfield.base.templatetags.qrcode import qrcode, qrcode_rounded
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


@patch("springfield.base.templatetags.qrcode.cache")
class TestQRCodeRounded(TestCase):
    def test_qrcode_rounded_cache_warm(self, cache_mock):
        cache_mock.get.return_value = "abc123base64=="
        result = str(qrcode_rounded("https://dude.abide"))
        assert 'src="data:image/png;base64,abc123base64=="' in result
        assert 'aria-hidden="true"' in result

    def test_qrcode_rounded_cache_cold_generates_png(self, cache_mock):
        cache_mock.get.return_value = None
        result = str(qrcode_rounded("https://dude.abide"))
        assert result.startswith('<img src="data:image/png;base64,')
        cache_mock.set.assert_called_once()

    def test_qrcode_rounded_returns_img_tag(self, cache_mock):
        cache_mock.get.return_value = None
        result = str(qrcode_rounded("https://dude.abide"))
        assert result.startswith("<img ")
        assert 'aria-hidden="true"' in result
