/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Adds role badges to locale names on the Wagtail locales list page.
 *
 * Data is provided by the mark_locale_roles_in_admin Wagtail hook, which injects
 * window.WAGTAIL_LOCALE_ALIAS_MAP = { "<locale_id>": "<fallback_code>", ... }
 * before this script is loaded.
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var list = document.getElementById('locales-list');
        if (!list) return;

        var aliasMap = window.WAGTAIL_LOCALE_ALIAS_MAP || {};

        Object.entries(aliasMap).forEach(function (entry) {
            var id = entry[0];
            var fallbackCode = entry[1];
            var a = list.querySelector('a[href$="/locales/edit/' + id + '/"]');
            if (a) {
                var badge = document.createElement('span');
                badge.className = 'w-status w-status--label';
                badge.textContent = 'alias \u2192 ' + fallbackCode;
                a.insertAdjacentElement('afterend', badge);
            }
        });
    });
})();
