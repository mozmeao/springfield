# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from hashlib import sha1
from io import BytesIO

from django.core.cache import caches

import qrcode as qr
from django_jinja import library
from markupsafe import Markup
from qrcode.image.svg import SvgPathFillImage

cache = caches["qrcode"]

FIREFOX_LOGO_SVG_URL = "/media/img/logos/firefox/firefox-logo.svg"

# Rounded SVG proportions, in modules.
DOT_RADIUS = 0.45
EYE_OUTER_RADIUS = 1.5
EYE_RING_RADIUS = 1.07
EYE_DOT_RADIUS = 0.75
LOGO_RATIO = 0.23  # of the full image width, quiet zone included
LOGO_GAP = 0.75  # clear space between the logo and the nearest dot


@library.global_function
def qrcode(data, box_size=20):
    key = sha1(f"{data}-{box_size}".encode()).hexdigest()
    svg = cache.get(key)
    if not svg:
        img = qr.make(data, image_factory=SvgPathFillImage, box_size=box_size)
        svg = BytesIO()
        img.save(svg)
        svg = svg.getvalue().decode("utf-8")
        cache.set(key, svg)

    return Markup(svg)


def _format_number(value):
    """Format an SVG coordinate with at most three decimals and no trailing zeros."""
    return f"{value:.3f}".rstrip("0").rstrip(".") or "0"


def _rounded_rect_path(left, top, size, radius):
    side = _format_number(size - 2 * radius)
    corner = _format_number(radius)
    arc = f"a{corner},{corner} 0 0 1"
    return (
        f"M{_format_number(left + radius)},{_format_number(top)}h{side}{arc} {corner},{corner}v{side}"
        f"{arc} -{corner},{corner}h-{side}{arc} -{corner},-{corner}v-{side}{arc} {corner},-{corner}z"
    )


@library.global_function
def qrcode_rounded_svg(data, box_size=20):
    """Inline SVG QR code with round dots, rounded finder eyes and a Firefox logo in the middle.

    Keeps the same outer markup as `qrcode()` (a white background `rect` and mm sizing) so existing
    CSS that hides the background or sizes the SVG still applies.
    """
    key = sha1(f"rounded-svg-{data}-{box_size}".encode()).hexdigest()
    svg = cache.get(key)
    if not svg:
        border = 4
        qr_code = qr.QRCode(error_correction=qr.constants.ERROR_CORRECT_H, border=border)
        qr_code.add_data(data)
        qr_code.make(fit=True)
        matrix = qr_code.get_matrix()
        size = len(matrix)
        module_count = size - 2 * border

        eye_origins = [(border, border), (border + module_count - 7, border), (border, border + module_count - 7)]

        def in_eye(col, row):
            return any(eye_col <= col < eye_col + 7 and eye_row <= row < eye_row + 7 for eye_col, eye_row in eye_origins)

        logo_size = size * LOGO_RATIO
        centre = size / 2
        clear_radius = logo_size / 2 + LOGO_GAP + DOT_RADIUS

        # Each dot is a zero-length line with a round cap, using relative moves to keep the markup small.
        dots = ["M0.5,0.5"]
        previous_col, previous_row = 0, 0
        for row, cells in enumerate(matrix):
            for col, is_dark in enumerate(cells):
                if not is_dark or in_eye(col, row):
                    continue
                if (col + 0.5 - centre) ** 2 + (row + 0.5 - centre) ** 2 < clear_radius**2:
                    continue
                dots.append(f"m{col - previous_col},{row - previous_row}h0")
                previous_col, previous_row = col, row

        # Each eye is an outer frame, a hole and a centre dot; evenodd fill punches the hole.
        eyes = []
        for eye_col, eye_row in eye_origins:
            eyes.append(_rounded_rect_path(eye_col, eye_row, 7, EYE_OUTER_RADIUS))
            eyes.append(_rounded_rect_path(eye_col + 1, eye_row + 1, 5, EYE_RING_RADIUS))
            eyes.append(_rounded_rect_path(eye_col + 2, eye_row + 2, 3, EYE_DOT_RADIUS))

        logo_offset = _format_number(centre - logo_size / 2)
        logo_width = _format_number(logo_size)
        dimension = f"{_format_number(size * box_size / 10)}mm"
        svg = (
            f'<svg width="{dimension}" height="{dimension}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
            f'<rect fill="white" x="0" y="0" width="100%" height="100%"/>'
            f'<path fill="none" stroke="black" stroke-width="{_format_number(DOT_RADIUS * 2)}" stroke-linecap="round" d="{"".join(dots)}"/>'
            f'<path fill-rule="evenodd" d="{"".join(eyes)}"/>'
            f'<image href="{FIREFOX_LOGO_SVG_URL}" x="{logo_offset}" y="{logo_offset}" width="{logo_width}" height="{logo_width}"/>'
            f"</svg>"
        )
        cache.set(key, svg)

    return Markup(svg)
