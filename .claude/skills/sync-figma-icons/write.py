# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Write exported SVGs into the repo and record their Figma hashes in the manifest.

Usage: python3 -I write.py <work dir> <exports json>
The exports JSON maps node ids to {"h": hash computed in Figma, "svg": text}. An SVG
whose text doesn't match its hash was copied wrong and is skipped, so re-export it.
"""

import json
import pathlib
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent
ICONS_DIR = SKILL_DIR.parents[2] / "media/img/firefox/flare/icons"
MANIFEST = SKILL_DIR / "manifest.json"


def fnv(text):
    value = 0x811C9DC5
    for char in text:
        value ^= ord(char)
        value = (value * 0x01000193) & 0xFFFFFFFF
    return format(value, "x")


def main(work_dir, exports_path):
    todo = json.loads((work_dir / "todo.json").read_text())
    exports = json.loads(exports_path.read_text())
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    mismatched = []
    for node_id, export in exports.items():
        if fnv(export["svg"]) != export["h"]:
            mismatched.append(node_id)
            continue
        target = ICONS_DIR / todo[node_id]["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(export["svg"])
        manifest[todo[node_id]["path"]] = export["h"]
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(exports) - len(mismatched)}/{len(exports)}", ("HASH MISMATCH, re-export: " + ",".join(mismatched)) if mismatched else "")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
