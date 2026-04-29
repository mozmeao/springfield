# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.templatetags.static import static

from springfield.cms.icon_utils import icon_value_fn

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

        # Collect all SVGs: icon value -> relative_path
        # icon_value_fn handles collisions: desktop-16 icons get short CSS names
        # (e.g. "forward"), colliding icons get dash-joined paths
        # (e.g. "mobile-24-arrows-chevrons-forward-24").
        value_to_rel = {}
        conflicts = []
        for svg_path in sorted(icon_dir.rglob("*.svg")):
            # Skip hidden files/dirs anywhere in the path
            if any(part.startswith(".") for part in svg_path.parts):
                continue
            rel = svg_path.relative_to(icon_dir)
            value = icon_value_fn(rel.with_suffix("").as_posix())
            if value in value_to_rel:
                conflicts.append((value, value_to_rel[value], rel))
            else:
                value_to_rel[value] = rel

        # Build CSS rules (values are already CSS-safe: no slashes)
        rules = [(f"fl-icon-{value}", rel) for value, rel in sorted(value_to_rel.items())]

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
                    f"\n{len(conflicts)} value collision(s) detected — two SVG files produced the same "
                    "icon value via icon_value_fn. The second file was skipped.\n\n"
                    "ACTION REQUIRED: add the colliding path(s) to _COLLIDING_PATHS in "
                    "springfield/cms/icon_utils.py, then re-run this command.\n"
                )
            )
            for value, existing_rel, new_rel in conflicts:
                self.stdout.write(self.style.WARNING(f'  COLLISION: value "{value}" → {existing_rel} vs {new_rel}\n'))
