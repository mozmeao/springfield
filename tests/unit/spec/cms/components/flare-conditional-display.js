/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import setupConditionalDisplay from '../../../../../media/js/cms/components/flare-conditional-display.es6';

const DAY_MS = 24 * 60 * 60 * 1000;

// Only the last-session condition is covered here — the others (version, geo,
// default browser, AI controls) predate this file and have no spec of their own.
describe('flare-conditional-display.es6.js — last-session condition', function () {
    let container;
    let originalUITour;

    function stubUITour(previousSessionEnd) {
        window.Mozilla.UITour = {
            ping: (cb) => cb(),
            getConfiguration: (key, cb) =>
                cb(key === 'appinfo' ? { previousSessionEnd } : {})
        };
    }

    function addWrapper(min, max) {
        const el = document.createElement('div');
        el.className = 'condition-last-session';
        if (min !== undefined) {
            el.dataset.minDaysSinceSession = min;
        }
        if (max !== undefined) {
            el.dataset.maxDaysSinceSession = max;
        }
        container.appendChild(el);
        return el;
    }

    function flush() {
        return new Promise((resolve) => setTimeout(resolve, 0));
    }

    beforeEach(function () {
        container = document.createElement('div');
        document.body.appendChild(container);
        originalUITour = window.Mozilla.UITour;
    });

    afterEach(function () {
        container.remove();
        document.documentElement.classList.remove(
            'firefox-is-default',
            'firefox-is-not-default',
            'ai-controls-available',
            'ai-controls-unavailable'
        );
        window.Mozilla.UITour = originalUITour;
    });

    it('reveals a min-only wrapper once the last session is far enough back', async function () {
        stubUITour(Date.now() - 30 * DAY_MS);
        const el = addWrapper(28, undefined);
        setupConditionalDisplay();
        await flush();
        expect(el.classList.contains('last-session-match')).toBe(true);
    });

    it('reveals a max-only wrapper while the last session is recent enough', async function () {
        stubUITour(Date.now() - 5 * DAY_MS);
        const el = addWrapper(undefined, 27);
        setupConditionalDisplay();
        await flush();
        expect(el.classList.contains('last-session-match')).toBe(true);
    });

    it('does not reveal a min-only wrapper when the last session is too recent', async function () {
        stubUITour(Date.now() - 5 * DAY_MS);
        const el = addWrapper(28, undefined);
        setupConditionalDisplay();
        await flush();
        expect(el.classList.contains('last-session-match')).toBe(false);
    });

    it('does not reveal a max-only wrapper when the last session is too old', async function () {
        stubUITour(Date.now() - 30 * DAY_MS);
        const el = addWrapper(undefined, 27);
        setupConditionalDisplay();
        await flush();
        expect(el.classList.contains('last-session-match')).toBe(false);
    });

    it('does not reveal when no previous session was ever recorded', async function () {
        // UITour's sentinel for "nothing recorded yet" is 0, not undefined.
        stubUITour(0);
        const el = addWrapper(28, undefined);
        setupConditionalDisplay();
        await flush();
        expect(el.classList.contains('last-session-match')).toBe(false);
    });
});
