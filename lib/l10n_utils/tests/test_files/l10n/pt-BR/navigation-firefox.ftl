# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Deliberately does NOT define navigation-download-firefox: that is the key
# missing in the fallback locale (pt-BR) but present in the alias locale
# (pt-PT), which is exactly the bug under test.
#
# navigation-browser is the inverse: present in the fallback locale but absent
# from the alias locale.
#
# navigation-features is defined in BOTH pt-PT and pt-BR (with different values):
navigation-browser = TEST-ptBR-browser
navigation-features = TEST-ptBR-features
