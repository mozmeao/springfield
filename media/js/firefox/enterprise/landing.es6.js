/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import MzpDetails from '@mozilla-protocol/core/protocol/js/details';

window.MzpDetails = MzpDetails;

function initMenuLists() {
    window.MzpDetails.init('.mzp-c-menu-list-title');
}

// This bundle can be loaded before the "lib" bundle that defines
// window.MzpSupports/MzpUtils (e.g. when rendered from a CMS block, whose
// position in the page is not guaranteed to be after "lib"). Deferring to
// DOMContentLoaded ensures all other page scripts have already run,
// regardless of where this script tag is placed.
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMenuLists);
} else {
    initMenuLists();
}
