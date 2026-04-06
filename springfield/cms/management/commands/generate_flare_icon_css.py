# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from collections import defaultdict

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.templatetags.static import static

from springfield.cms.icon_utils import icon_css_name

CSS_HEADER = """\
/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 *
 * Run: python manage.py generate_flare_icon_css --icon-dir <path> --output <path>
 */
"""


class Command(BaseCommand):
    help = "Generate fl-icon-* CSS classes from SVG files in a directory."

    def add_arguments(self, parser):
        parser.add_argument(
            "--icon-dir",
            required=True,
            help="Path to the icon directory to scan, relative to the repo root.",
        )
        parser.add_argument(
            "--output",
            required=True,
            help="CSS file to write, relative to the repo root.",
        )

    def handle(self, *args, **options):
        repo_root = settings.ROOT_PATH
        icon_dir = repo_root / options["icon_dir"]
        output_path = repo_root / options["output"]

        if not icon_dir.is_dir():
            raise CommandError(f"Icon directory not found: {icon_dir}")

        # Compute the path of icon_dir relative to whichever STATICFILES_DIRS entry contains it.
        # This lets us use django's static() to produce the correct URL regardless of STATIC_URL.
        icon_dir_static_path = None
        for static_dir in settings.STATICFILES_DIRS:
            try:
                icon_dir_static_path = icon_dir.relative_to(static_dir)
                break
            except ValueError:
                continue
        if icon_dir_static_path is None:
            raise CommandError(f"Icon dir {icon_dir} is not under any path in STATICFILES_DIRS. Ensure it is accessible as a static file.")

        # Collect all SVGs: stem -> list of (parent_folder_name, relative_path)
        stem_index = defaultdict(list)
        for svg_path in sorted(icon_dir.rglob("*.svg")):
            # Skip hidden files/dirs anywhere in the path
            if any(part.startswith(".") for part in svg_path.parts):
                continue
            rel = svg_path.relative_to(icon_dir)
            stem = svg_path.stem
            parent = rel.parent.name  # immediate parent folder name
            stem_index[stem].append((parent, rel))

        # Build class name -> relative_path mapping
        rules = []
        conflicts = []
        for stem, entries in sorted(stem_index.items()):
            css_name = icon_css_name(stem)
            if len(entries) == 1:
                parent, rel = entries[0]
                class_name = f"fl-icon-{css_name}"
                rules.append((class_name, rel))
            else:
                conflicts.append(stem)
                for parent, rel in sorted(entries, key=lambda e: e[1]):
                    class_name = f"fl-icon-{parent}-{css_name}"
                    rules.append((class_name, rel))

        # Write CSS
        lines = [CSS_HEADER]
        for class_name, rel in rules:
            url = static(f"{icon_dir_static_path.as_posix()}/{rel.as_posix()}")
            lines.append(f".{class_name} {{\n    --icon-src: url('{url}');\n}}\n")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines))

        self.stdout.write(f"Generated {len(rules)} rules → {options['output']}\n")

        if conflicts:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{len(conflicts)} filename conflict(s) detected. Conflicting filenames have been "
                    "prefixed with their parent folder name in the generated CSS.\n\n"
                    "ACTION REQUIRED: There may be code (for example, see "
                    "IconListItemValue.icon_name in springfield/cms/blocks.py) that relies on "
                    "only the filename (e.g. 'test') being used in a CSS class. For conflicting "
                    "icons (like 'arrows/test.svg' and 'user/test.svg') the code must use "
                    "a combination of the parent folder name and the filename (e.g. 'arrows-test' "
                    "or 'user-test') to match the generated CSS class. Please either: \n"
                    "    A. update the relevant code (for example, `IconListItemValue.icon_name`) "
                    "for each of the conflicts detected here, OR\n"
                    "    B. rename the conflicting filenames ('arrows/test.svg' and 'user/test.svg').\n"
                    "Then re-run this command.\n"
                )
            )
            for stem in conflicts:
                entries = stem_index[stem]
                class_names = ", ".join(f"fl-icon-{parent}-{icon_css_name(stem)}" for parent, _ in entries)
                self.stdout.write(self.style.WARNING(f'  CONFLICT: stem "{stem}" → {class_names}\n'))
