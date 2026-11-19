# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import re
from unittest.mock import patch

import qrcode as qr
from bs4 import BeautifulSoup
from qrcode.image.svg import SvgPathFillImage

from springfield.base.templatetags.qrcode import FIREFOX_LOGO_SVG_URL, qrcode, qrcode_rounded_svg
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
class TestQRCodeRoundedSvg(TestCase):
    def test_cache_warm(self, cache_mock):
        cache_mock.get.return_value = "<svg>stuff</svg>"
        assert str(qrcode_rounded_svg("https://dude.abide")) == "<svg>stuff</svg>"
        cache_mock.set.assert_not_called()

    def test_cache_cold_generates_svg(self, cache_mock):
        cache_mock.get.return_value = None
        result = str(qrcode_rounded_svg("https://dude.abide", 12))
        assert result.startswith("<svg ")
        cache_mock.set.assert_called_once()

    def test_keeps_markup_existing_css_relies_on(self, cache_mock):
        cache_mock.get.return_value = None
        svg = BeautifulSoup(str(qrcode_rounded_svg("https://dude.abide", 12)), "html.parser").find("svg")
        assert svg["width"].endswith("mm")
        assert svg["width"] == svg["height"]
        # The background is the only rect, so CSS that hides it leaves the code itself visible.
        rects = svg.find_all("rect")
        assert len(rects) == 1
        assert rects[0]["fill"] == "white"

    def test_draws_round_dots_eyes_and_logo(self, cache_mock):
        cache_mock.get.return_value = None
        svg = BeautifulSoup(str(qrcode_rounded_svg("https://dude.abide")), "html.parser").find("svg")
        dots, eyes = svg.find_all("path")
        assert dots["stroke-linecap"] == "round"
        assert eyes["fill-rule"] == "evenodd"
        # Three eyes, each an outer frame, a hole and a centre dot.
        assert eyes["d"].count("M") == 9
        assert svg.find("image")["href"] == FIREFOX_LOGO_SVG_URL

    def test_dots_match_the_qr_matrix(self, cache_mock):
        cache_mock.get.return_value = None
        for data in (
            "https://mzl.la/fxcomnavbutton?r=qr",
            "https://www.firefox.com/browsers/mobile/app/?product=firefox&campaign=firefox-com-mobile-page",
        ):
            with self.subTest(data=data):
                svg = BeautifulSoup(str(qrcode_rounded_svg(data)), "html.parser").find("svg")
                dots_path = svg.find("path")["d"]

                drawn = set()
                col, row = 0, 0
                for col_step, row_step in re.findall(r"m(-?\d+),(-?\d+)h0", dots_path):
                    col, row = col + int(col_step), row + int(row_step)
                    drawn.add((col, row))

                qr_code = qr.QRCode(error_correction=qr.constants.ERROR_CORRECT_H, border=4)
                qr_code.add_data(data)
                qr_code.make(fit=True)
                matrix = qr_code.get_matrix()
                size = len(matrix)
                eye_origins = [(4, 4), (size - 11, 4), (4, size - 11)]
                dark_outside_eyes = {
                    (col, row)
                    for row, cells in enumerate(matrix)
                    for col, is_dark in enumerate(cells)
                    if is_dark and not any(eye_col <= col < eye_col + 7 and eye_row <= row < eye_row + 7 for eye_col, eye_row in eye_origins)
                }

                assert drawn <= dark_outside_eyes, "Every dot sits on a dark module"
                hidden = dark_outside_eyes - drawn
                # Only modules under the centred logo are left out.
                logo_reach = size * 0.23 / 2 + 2
                assert all(abs(col + 0.5 - size / 2) < logo_reach and abs(row + 0.5 - size / 2) < logo_reach for col, row in hidden)
                # Level H recovers up to 30% of the code; the logo must hide far less than that.
                data_modules = (size - 8) ** 2
                assert len(hidden) < data_modules * 0.15
