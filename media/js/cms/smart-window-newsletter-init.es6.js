/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const ctaButton = document.getElementById('smart-window-cta');
const newsletterForm = document.getElementById('newsletter-form');

if (ctaButton && newsletterForm) {
    ctaButton.addEventListener('click', () => {
        ctaButton.classList.add('hidden');
        newsletterForm.classList.remove('hidden');
    });
}
