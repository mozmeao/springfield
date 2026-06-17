# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Test value — exists only in this test fixture, never in live l10n data.
# A test asserting on this string proves the pt-PT (alias) bundle was the source.
#
# navigation-browser is deliberately ABSENT here: it is the "present in the
# fallback locale (pt-BR), missing in the alias locale (pt-PT)" key used to test
# that fallback-locale strings still win once the alias joins the chain.
navigation-download-firefox = TEST-ptPT-download
