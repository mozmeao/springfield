# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Layout for `qrcode_with_logo`, matching Firefox's built-in QR code generator.
# Per ISO/IEC 18004, finder patterns are always 7x7 modules.

# Translated from https://searchfox.org/firefox-main/source/browser/components/qrcode/QRCodeWorker.worker.mjs
# Only Firefox includes these natively so we need to implement these ourselves for other browsers

import base64
import math
import os
from hashlib import sha1
from io import BytesIO

from django.conf import settings
from django.core.cache import caches

import qrcode as qr
from django_jinja import library
from markupsafe import Markup
from PIL import Image, ImageDraw
from qrcode.exceptions import DataOverflowError

cache = caches["qrcode"]

FIREFOX_LOGO_PNG = os.path.join(settings.ROOT_PATH, "media/img/logos/firefox/firefox-logo-white-bg.png")
FINDER_SIZE = 7
LOGO_QR_CELL_SIZE = 20
# Per ISO/IEC 18004, the minimum quiet zone around the code is 4 modules.
LOGO_QR_MARGIN_CELLS = 4
# 0.4 makes each dot 80% of the cell width, leaving a gap between neighbours.
DOT_RADIUS_FACTOR = 0.4
FINDER_OUTER_CORNER_RADIUS_FACTOR = 1.2
FINDER_INNER_CORNER_RADIUS_FACTOR = 0.6
# Below 6 modules the logo is too small to recognise; above 8 it exceeds the M-level error correction budget.
MIN_LOGO_MODULE_SPAN = 6
MAX_LOGO_MODULE_SPAN = 8
# Share of the image width the logo aims for, before the module limits above.
LOGO_CANVAS_RATIO = 0.18
# Pillow draws without anti-aliasing, so draw this many times larger and scale down for smooth edges.
SUPERSAMPLE = 4
LOGO_QR_LOGO_PNG = FIREFOX_LOGO_PNG


def _encode_logo_qr_matrix(data):
    """Return the module matrix and whether there is room for the logo.

    M-level error correction leaves enough headroom for the centred logo. Data
    that only fits at L is drawn without the logo, since L's ~7% budget is too
    narrow to spare.
    """

    def encode(level):
        qr_obj = qr.QRCode(error_correction=level, border=0)
        qr_obj.add_data(data)
        qr_obj.make(fit=True)
        return qr_obj.get_matrix()

    try:
        return encode(qr.constants.ERROR_CORRECT_M), True
    except DataOverflowError:
        return encode(qr.constants.ERROR_CORRECT_L), False


def _draw_finder_pattern(draw, x, y, cell):
    """Draw one finder pattern: a 7x7 dark square, a 5x5 light ring and a 3x3 dark centre, all rounded."""
    outer_radius = round(cell * FINDER_OUTER_CORNER_RADIUS_FACTOR)
    inner_radius = round(cell * FINDER_INNER_CORNER_RADIUS_FACTOR)
    for inset, fill, radius in ((0, "black", outer_radius), (1, "white", inner_radius), (2, "black", inner_radius)):
        start = inset * cell
        end = (FINDER_SIZE - inset) * cell - 1
        draw.rounded_rectangle([x + start, y + start, x + end, y + end], radius=radius, fill=fill)


def _render_logo_qr_png(data):
    matrix, show_logo = _encode_logo_qr_matrix(data)
    dot_count = len(matrix)

    final_size = (dot_count + 2 * LOGO_QR_MARGIN_CELLS) * LOGO_QR_CELL_SIZE
    logo_size = round(final_size * LOGO_CANVAS_RATIO)
    logo_size = min(logo_size, MAX_LOGO_MODULE_SPAN * LOGO_QR_CELL_SIZE)
    logo_size = max(logo_size, MIN_LOGO_MODULE_SPAN * LOGO_QR_CELL_SIZE) * SUPERSAMPLE

    cell = LOGO_QR_CELL_SIZE * SUPERSAMPLE
    margin = LOGO_QR_MARGIN_CELLS * cell
    size = final_size * SUPERSAMPLE
    center = size / 2
    dot_radius = cell * DOT_RADIUS_FACTOR
    # Dots that would touch the logo are left out; error correction recovers them.
    clear_radius = logo_size / 2 + dot_radius

    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)

    last = dot_count - FINDER_SIZE
    finder_origins = ((0, 0), (0, last), (last, 0))
    for row, line in enumerate(matrix):
        for col, is_dark in enumerate(line):
            in_finder = any(r <= row < r + FINDER_SIZE and c <= col < c + FINDER_SIZE for r, c in finder_origins)
            if not is_dark or in_finder:
                continue
            x = margin + (col + 0.5) * cell
            y = margin + (row + 0.5) * cell
            if show_logo and math.hypot(x - center, y - center) < clear_radius:
                continue
            draw.ellipse([x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius], fill="black")

    for row, col in finder_origins:
        _draw_finder_pattern(draw, margin + col * cell, margin + row * cell, cell)

    if show_logo:
        with Image.open(LOGO_QR_LOGO_PNG) as logo:
            logo = logo.convert("RGBA")
            scale = logo_size / max(logo.size)
            logo = logo.resize((round(logo.width * scale), round(logo.height * scale)), Image.Resampling.LANCZOS)
            img.paste(logo, (round(center - logo.width / 2), round(center - logo.height / 2)), logo)

    img = img.resize((final_size, final_size), Image.Resampling.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@library.global_function
def qrcode_with_logo(data):
    """Render `data` as a PNG QR code with round dots, rounded finder patterns and a centred Firefox logo.

    Port of the QR code generator built into Firefox.
    """
    key = sha1(f"logo-{data}".encode()).hexdigest()
    b64 = cache.get(key)
    if not b64:
        b64 = base64.b64encode(_render_logo_qr_png(data)).decode()
        cache.set(key, b64)
    return Markup(f'<img src="data:image/png;base64,{b64}" alt="" aria-hidden="true">')
