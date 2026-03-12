/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * Smart Window waitlist form handling for unsupported countries.
 * Adapted from firefox/ai/waitlist-newsletter-init.es6.js.
 */

import MzpNewsletter from '@mozilla-protocol/core/protocol/js/newsletter';

const successCustomCallback = () => {
    const newsletters = Array.from(
        document.querySelectorAll(
            ".mzp-c-newsletter-form input[name='newsletters']:checked"
        )
    ).map((newsletter) => newsletter.value);

    if (window.dataLayer) {
        for (let i = 0; i < newsletters.length; ++i) {
            window.dataLayer.push({
                event: 'newsletter_subscribe',
                newsletter_id: newsletters[i]
            });
        }
    }

    // Hide form content, show confirmation
    const formContent = document.querySelector(
        '#state-waitlist .c-smart-window-content'
    );
    if (formContent) {
        formContent.style.display = 'none';
    }

    const confirmation = document.getElementById('waitlist-confirmation');
    if (confirmation) {
        confirmation.classList.remove('hidden');
    }

    document.body.scrollTo(0, 0);
};

MzpNewsletter.init(successCustomCallback);
