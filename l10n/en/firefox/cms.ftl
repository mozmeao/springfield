# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

### These are strings used inside templates that are part of the
### Content Management System. It means they can be used to build new
### pages that have some specificities depending on the page type.

# Download Firefox Page

# Page title - Download Firefox for macOS/Windows/Linux
# Variables:
#   $platform (string) - Currently selected platform for download
firefox-download-for = Download <span class="fl-fx-logo"></span> { -brand-name-firefox } for <span class="fl-platform-select js-platform-select" data-platform="{ $platform }">{ $platform }</span>
