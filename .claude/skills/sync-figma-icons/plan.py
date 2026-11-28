# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Decide which Figma icons to export and where each one goes in the repo.

Usage: python3 -I plan.py <work dir> [--full]
Reads <work dir>/inventory.txt (one `platform|category / name|node id|hash` row per
icon) and writes <work dir>/todo.json plus <work dir>/batches/NN.txt.
"""

import json
import pathlib
import re
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent
ICONS_DIR = SKILL_DIR.parents[2] / "media/img/firefox/flare/icons"
MANIFEST = SKILL_DIR / "manifest.json"
FOLDER_PRIORITY = [
    "desktop-16",
    "desktop-20",
    "mobile-24",
    "mobile-20",
    "mobile-16",
    "desktop-12",
    "desktop-32",
    "desktop-40",
    "desktop-10",
    "mobile-48",
    "mobile-72",
]
SKIPPED_NAMES = {"avatar-signed-in-fill-profile-picture-16"}  # embeds a photo, which can't work as a mask
BATCH_SIZE = 20


def base_name(name):
    return re.sub(r"-\d+$", "", name)


def folder_slug(category, platform):
    slug = re.sub(r"['():]", "", category.lower()).replace("&", "and" if platform == "desktop" else "")
    return re.sub(r"[^a-z0-9]+", "-", slug).strip("-")


def plan(inventory_rows, repo_paths, manifest, full):
    """Return {node id: {"path", "hash"}} for every Figma icon to export.

    An icon updates the repo file with the same platform and name. An icon whose
    name exists in no size at all is new and gets one sample, preferring an
    existing folder; other sizes of icons already in the repo are left out.
    """
    existing = {(path.split("-")[0], pathlib.PurePath(path).stem.lower()): path for path in repo_paths if path.count("/") == 2}
    repo_bases = {base_name(pathlib.PurePath(path).stem.lower()) for path in repo_paths}
    repo_folders = {path.rsplit("/", 1)[0] for path in repo_paths}

    exports, new_icons, seen = {}, {}, set()
    for row in inventory_rows:
        platform, full_name, node_id, figma_hash = row.split("|")
        category, _, name = full_name.rpartition("/")
        name = name.strip().lower()
        size = re.search(r"-(\d+)$", name)
        if name in SKIPPED_NAMES or not size or (platform, name) in seen:
            continue
        seen.add((platform, name))
        if (platform, name) in existing:
            path = existing[(platform, name)]
            if full or manifest.get(path) != figma_hash:
                exports[node_id] = {"path": path, "hash": figma_hash}
        elif base_name(name) not in repo_bases:
            path = f"{platform}-{size.group(1)}/{folder_slug(category.strip(), platform)}/{name}.svg"
            new_icons.setdefault(base_name(name), []).append({"node_id": node_id, "path": path, "hash": figma_hash})

    def preference(candidate):
        size_folder = candidate["path"].split("/")[0]
        size_rank = FOLDER_PRIORITY.index(size_folder) if size_folder in FOLDER_PRIORITY else len(FOLDER_PRIORITY)
        return (candidate["path"].rsplit("/", 1)[0] not in repo_folders, size_rank)

    for candidates in new_icons.values():
        best = min(candidates, key=preference)
        exports[best["node_id"]] = {"path": best["path"], "hash": best["hash"]}
    return exports


def self_check():
    rows = [
        "desktop|globe / globe-16|1:1|aaa",
        "desktop|globe / globe-12|1:2|bbb",
        "mobile|sports / golf-32|1:3|ccc",
        "desktop|sports / golf-32|1:4|ddd",
        "desktop|avatars / avatar-signed-in-fill-profile-picture-16|1:5|eee",
    ]
    repo_paths = ["desktop-16/globe/globe-16.svg"]
    manifest = {"desktop-16/globe/globe-16.svg": "aaa"}
    assert plan(rows, repo_paths, manifest, full=False) == {"1:4": {"path": "desktop-32/sports/golf-32.svg", "hash": "ddd"}}
    assert set(plan(rows, repo_paths, manifest, full=True)) == {"1:1", "1:4"}
    assert folder_slug("arrows & chevrons", "desktop") == "arrows-and-chevrons"
    assert folder_slug("tabs: audio & media", "mobile") == "tabs-audio-media"


def main(work_dir, full):
    self_check()
    repo_paths = [path.relative_to(ICONS_DIR).as_posix() for path in ICONS_DIR.rglob("*.svg") if not any(part.startswith(".") for part in path.parts)]
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    exports = plan((work_dir / "inventory.txt").read_text().splitlines(), repo_paths, manifest, full)

    (work_dir / "todo.json").write_text(json.dumps(exports, indent=1))
    batches_dir = work_dir / "batches"
    batches_dir.mkdir(exist_ok=True)
    for old_batch in batches_dir.glob("*.txt"):
        old_batch.unlink()
    node_ids = list(exports)
    for start in range(0, len(node_ids), BATCH_SIZE):
        (batches_dir / f"{start // BATCH_SIZE + 1:02d}.txt").write_text(",".join(node_ids[start : start + BATCH_SIZE]))

    new_count = sum(not (ICONS_DIR / export["path"]).exists() for export in exports.values())
    print(f"{len(exports)} to export ({len(exports) - new_count} updates, {new_count} new) in {-(-len(node_ids) // BATCH_SIZE)} batches")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), full="--full" in sys.argv)
