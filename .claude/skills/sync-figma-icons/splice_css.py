# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Replace the generated rules in flare-icon.css, keeping the hand-written parts.

Usage: python3 -I splice_css.py <css written by generate_flare_icon_css>
"""

import pathlib
import sys

CSS_FILE = pathlib.Path(__file__).resolve().parents[3] / "media/css/cms/components/flare-icon.css"
START_MARKER = "/* --- Generated icon rules (python manage.py generate_flare_icon_css) --- */\n\n"
END_MARKER = "\n/* --- Hand-maintained overrides"

css = CSS_FILE.read_text()
generated = pathlib.Path(sys.argv[1]).read_text()
rules = generated[generated.index("*/\n") + 3 :].strip("\n") + "\n"
start = css.index(START_MARKER) + len(START_MARKER)
CSS_FILE.write_text(css[:start] + rules + css[css.index(END_MARKER) :])
