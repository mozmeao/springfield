/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import Plausible from './plausible.es6';

const TrackCTAClick = {};

TrackCTAClick.selector = '[data-cta-text], [data-cta-uid]';

TrackCTAClick.attributes = {
    'data-cta-text': 'cta_text',
    'data-cta-uid': 'cta_uid',
    'data-cta-position': 'cta_position',
    'data-cta-type': 'cta_type'
};

/**
 * Create the cta_click props from an element's data-cta-* attributes
 * @param {Element} el
 * @returns {Object}
 */
TrackCTAClick.getProps = (element) => {
    const props = {};

    for (const [attribute, prop] of Object.entries(TrackCTAClick.attributes)) {
        const value = (element.getAttribute(attribute) || '').trim();
        if (value) {
            props[prop] = value;
        }
    }

    return props;
};

/**
 * Sends a cta_click event to Plausible for clicks on or inside a CTA
 * @param {Event} event
 */
TrackCTAClick.handleClick = (event) => {
    try {
        const target = event.target;
        if (!(target instanceof Element)) {
            return;
        }

        const el = target.closest(TrackCTAClick.selector);
        if (!el) {
            return;
        }

        const props = TrackCTAClick.getProps(el);
        if (!props.cta_text && !props.cta_uid) {
            return;
        }

        Plausible.trackEvent('cta_click', props);
    } catch (error) {
        // Don't let analytics break the click
    }
};

TrackCTAClick.init = () => {
    // bubble phase to match GTM's click triggers
    document.addEventListener('click', TrackCTAClick.handleClick);
};

export default TrackCTAClick;
