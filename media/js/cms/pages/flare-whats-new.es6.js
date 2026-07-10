/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const setUpWhatsNewPage = () => {
    const updatedNotification = document.querySelector(
        '#firefox-has-been-updated'
    );
    if (updatedNotification && window.location.search.includes('fromMainNav')) {
        updatedNotification.style.display = 'none';
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setUpWhatsNewPage);
} else {
    setUpWhatsNewPage();
}
