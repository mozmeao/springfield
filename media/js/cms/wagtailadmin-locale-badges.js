/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Adds role badges to locale names on the Wagtail locales list page.
 *
 * Data is provided by the mark_locale_roles_in_admin Wagtail hook, which injects
 * window.WAGTAIL_LOCALE_ALIAS_MAP = { "<locale_id>": "<fallback_code>", ... } and
 * window.WAGTAIL_LOCALE_NOTE_MAP = { "<locale_id>": "<badge text>", ... }
 * before this script is loaded.
 */

(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var list = document.getElementById('locales-list');
        if (!list) return;

        // A locale can earn more than one badge. 'afterend' always inserts directly
        // after its anchor, so appending to the last badge keeps them in call order.
        var lastBadgeByLocale = {};

        function addBadge(localeId, text) {
            var anchor = list.querySelector(
                'a[href$="/locales/edit/' + localeId + '/"]'
            );
            if (!anchor) return;
            var badge = document.createElement('span');
            badge.className = 'w-status w-status--label locale-role-badge';
            badge.textContent = text;
            (lastBadgeByLocale[localeId] || anchor).insertAdjacentElement(
                'afterend',
                badge
            );
            lastBadgeByLocale[localeId] = badge;
        }

        var aliasMap = window.WAGTAIL_LOCALE_ALIAS_MAP || {};
        Object.entries(aliasMap).forEach(function (entry) {
            addBadge(entry[0], 'alias \u2192 ' + entry[1]);
        });

        var noteMap = window.WAGTAIL_LOCALE_NOTE_MAP || {};
        Object.entries(noteMap).forEach(function (entry) {
            addBadge(entry[0], entry[1]);
        });
    });
})();
