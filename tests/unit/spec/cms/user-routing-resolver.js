/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/* global require */

/* For reference read the Jasmine and Sinon docs
 * Jasmine docs: https://jasmine.github.io/
 * Sinon docs: http://sinonjs.org/docs/
 */

// The resolver is an IIFE that boots (mutates window.location, reads DOM
// blobs) as soon as it's loaded. Set the autoboot flag BEFORE requiring
// the module so the IIFE only exposes its pure functions. CommonJS
// require() is used (not ES import) so this pre-flag assignment runs
// first — ES imports would hoist ahead of it.
window.Mozilla = window.Mozilla || {};
window.Mozilla.UserRoutingResolver = { autoboot: false };

require('../../../../media/js/cms/user-routing-resolver.js');

describe('user-routing-resolver.js', function () {
    const ns = window.Mozilla.UserRoutingResolver;

    // -------------------------------------------------------------------
    // conditionMatches — the tri-state atom
    // -------------------------------------------------------------------

    describe('conditionMatches', function () {
        it('returns true when a resolved value is in the values list under op=is', function () {
            const c = { signal: 'country', op: 'is', values: ['US', 'CA'] };
            expect(ns.conditionMatches(c, { country: 'US' })).toBe(true);
        });

        it('returns false when a resolved value is NOT in the values list under op=is', function () {
            const c = { signal: 'country', op: 'is', values: ['US'] };
            expect(ns.conditionMatches(c, { country: 'DE' })).toBe(false);
        });

        it('inverts the check under op=is_not', function () {
            const c = { signal: 'country', op: 'is_not', values: ['US'] };
            expect(ns.conditionMatches(c, { country: 'DE' })).toBe(true);
            expect(ns.conditionMatches(c, { country: 'US' })).toBe(false);
        });

        it('returns null when the signal name is not present in resolved (still pending)', function () {
            const c = { signal: 'country', op: 'is', values: ['US'] };
            expect(ns.conditionMatches(c, {})).toBeNull();
        });

        it('returns false when the resolved value is explicitly undefined (fetched, no answer)', function () {
            const c = { signal: 'country', op: 'is', values: ['US'] };
            expect(ns.conditionMatches(c, { country: undefined })).toBe(false);
        });

        it('returns false for an empty values list', function () {
            const c = { signal: 'country', op: 'is', values: [] };
            expect(ns.conditionMatches(c, { country: 'US' })).toBe(false);
        });

        it('returns false when the signal name is missing from the condition', function () {
            expect(
                ns.conditionMatches(
                    { op: 'is', values: ['US'] },
                    { country: 'US' }
                )
            ).toBe(false);
        });

        it('handles bool values correctly (indexOf strict equality)', function () {
            const c = { signal: 'lapsed_user', op: 'is', values: [true] };
            expect(ns.conditionMatches(c, { lapsed_user: true })).toBe(true);
            expect(ns.conditionMatches(c, { lapsed_user: false })).toBe(false);
        });
    });

    // -------------------------------------------------------------------
    // ruleMatches — AND across conditions, tri-state result
    // -------------------------------------------------------------------

    describe('ruleMatches', function () {
        it('returns true when every condition matches', function () {
            const rule = {
                conditions: [
                    { signal: 'country', op: 'is', values: ['US'] },
                    { signal: 'lapsed_user', op: 'is', values: [true] }
                ]
            };
            expect(
                ns.ruleMatches(rule, { country: 'US', lapsed_user: true })
            ).toBe(true);
        });

        it('returns false when any condition fails (AND short-circuit)', function () {
            const rule = {
                conditions: [
                    { signal: 'country', op: 'is', values: ['US'] },
                    { signal: 'lapsed_user', op: 'is', values: [true] }
                ]
            };
            expect(
                ns.ruleMatches(rule, { country: 'US', lapsed_user: false })
            ).toBe(false);
        });

        it('returns null when a condition is pending and none has definitively failed', function () {
            const rule = {
                conditions: [
                    { signal: 'country', op: 'is', values: ['US'] },
                    { signal: 'ai_controls', op: 'is', values: ['available'] }
                ]
            };
            // country matches, ai_controls not yet in resolved → still pending
            expect(ns.ruleMatches(rule, { country: 'US' })).toBeNull();
        });

        it('short-circuits to false when one condition is definitively false, even if others are pending', function () {
            // The precedence check the server-side evaluator used to enforce:
            // waiting on a UITour signal is pointless if the whole rule has
            // already lost on a resolved sync signal.
            const rule = {
                conditions: [
                    { signal: 'country', op: 'is', values: ['US'] },
                    { signal: 'ai_controls', op: 'is', values: ['available'] }
                ]
            };
            expect(ns.ruleMatches(rule, { country: 'DE' })).toBe(false);
        });

        it('returns false for a rule with no conditions (never spontaneously matches)', function () {
            expect(ns.ruleMatches({ conditions: [] }, {})).toBe(false);
            expect(ns.ruleMatches({}, {})).toBe(false);
        });
    });

    // -------------------------------------------------------------------
    // evaluate() closes over the module-scope rules array populated at
    // boot. It's covered indirectly by the ruleMatches tests above and by
    // the integration tests that exercise the full boot lifecycle
    // (springfield/firefox/tests/test_wnp_dispatch.py checks the JSON
    // contract the browser resolver consumes).
    // -------------------------------------------------------------------
    // SYNC_RESOLVERS — DOM / URL / Mozilla.Client readers
    // -------------------------------------------------------------------

    describe('SYNC_RESOLVERS.country', function () {
        afterEach(function () {
            document.documentElement.removeAttribute('data-country-code');
        });

        it('reads data-country-code from <html> and upper-cases it', function () {
            document.documentElement.setAttribute('data-country-code', 'de');
            expect(ns.SYNC_RESOLVERS.country()).toBe('DE');
        });

        it('returns undefined when the attribute is missing', function () {
            expect(ns.SYNC_RESOLVERS.country()).toBeUndefined();
        });

        it('returns undefined when the attribute is empty', function () {
            document.documentElement.setAttribute('data-country-code', '');
            expect(ns.SYNC_RESOLVERS.country()).toBeUndefined();
        });
    });

    describe('SYNC_RESOLVERS.lapsed_user', function () {
        // Stub location by replacing the getter on window.location — the
        // resolver reads pathname + search off `window.location`, so we
        // intercept there. Sinon can't stub `location` directly on all
        // browsers, so use Object.defineProperty on a scratch object.
        let savedHref;
        beforeEach(function () {
            savedHref = window.location.href;
        });
        afterEach(function () {
            // Restore by pushing state; the test URL is under the same origin
            // when tests run under jasmine-browser-runner.
            try {
                window.history.replaceState({}, '', savedHref);
            } catch (e) {
                /* ignore */
            }
        });

        function setLocation(pathname, search) {
            window.history.replaceState({}, '', pathname + (search || ''));
        }

        it('returns true when target - old >= LAPSED_MIN_GAP', function () {
            setLocation('/en-US/whatsnew/156/', '?oldversion=149');
            expect(ns.SYNC_RESOLVERS.lapsed_user()).toBe(true);
        });

        it('returns false when the gap is smaller than LAPSED_MIN_GAP', function () {
            setLocation('/en-US/whatsnew/156/', '?oldversion=155');
            expect(ns.SYNC_RESOLVERS.lapsed_user()).toBe(false);
        });

        it('accepts an optional rv: prefix on oldversion (parity with the deleted server regex)', function () {
            // Regression guard for the reviewed bug: server used to accept
            // `oldversion=rv:149`; parseInt does not.
            setLocation('/en-US/whatsnew/156/', '?oldversion=rv:149');
            expect(ns.SYNC_RESOLVERS.lapsed_user()).toBe(true);
        });

        it('returns undefined when the path does not match /whatsnew/{n}/', function () {
            setLocation('/en-US/firefox/', '?oldversion=149');
            expect(ns.SYNC_RESOLVERS.lapsed_user()).toBeUndefined();
        });

        it('returns undefined when oldversion is missing', function () {
            setLocation('/en-US/whatsnew/156/');
            expect(ns.SYNC_RESOLVERS.lapsed_user()).toBeUndefined();
        });

        it('returns undefined when oldversion is unparseable', function () {
            setLocation('/en-US/whatsnew/156/', '?oldversion=not-a-number');
            expect(ns.SYNC_RESOLVERS.lapsed_user()).toBeUndefined();
        });
    });

    describe('SYNC_RESOLVERS.platform', function () {
        let savedPlatform;
        beforeEach(function () {
            savedPlatform =
                window.Mozilla && window.Mozilla.Client
                    ? window.Mozilla.Client.platform
                    : undefined;
        });
        afterEach(function () {
            if (window.Mozilla && window.Mozilla.Client) {
                window.Mozilla.Client.platform = savedPlatform;
            }
        });

        it('passes through the known platforms unchanged', function () {
            window.Mozilla.Client.platform = 'windows';
            expect(ns.SYNC_RESOLVERS.platform()).toBe('windows');
            window.Mozilla.Client.platform = 'osx';
            expect(ns.SYNC_RESOLVERS.platform()).toBe('osx');
        });

        it('coerces the "other" bucket to "other-os" (matches CMS enum values)', function () {
            // Regression guard: without the coercion, marketing rules using
            // the "other-os" dropdown value silently never match.
            window.Mozilla.Client.platform = 'other';
            expect(ns.SYNC_RESOLVERS.platform()).toBe('other-os');
        });

        it('returns undefined when Mozilla.Client is missing', function () {
            const savedClient = window.Mozilla.Client;
            delete window.Mozilla.Client;
            try {
                expect(ns.SYNC_RESOLVERS.platform()).toBeUndefined();
            } finally {
                window.Mozilla.Client = savedClient;
            }
        });
    });

    describe('SYNC_RESOLVERS.firefox_version', function () {
        let savedIsFirefox;
        let savedVer;
        beforeEach(function () {
            savedIsFirefox = window.Mozilla.Client.isFirefox;
            savedVer = window.Mozilla.Client.FirefoxMajorVersion;
        });
        afterEach(function () {
            window.Mozilla.Client.isFirefox = savedIsFirefox;
            window.Mozilla.Client.FirefoxMajorVersion = savedVer;
        });

        it('returns the major version when the browser is Firefox', function () {
            window.Mozilla.Client.isFirefox = true;
            window.Mozilla.Client.FirefoxMajorVersion = 156;
            expect(ns.SYNC_RESOLVERS.firefox_version()).toBe(156);
        });

        it('returns undefined on non-Firefox UAs (isFirefox false)', function () {
            // Regression guard: Mozilla.Client.FirefoxMajorVersion is 0 on
            // non-Firefox; without the isFirefox guard, `firefox_version
            // is_not [200]` would fire on every Chrome/Safari visitor.
            window.Mozilla.Client.isFirefox = false;
            window.Mozilla.Client.FirefoxMajorVersion = 0;
            expect(ns.SYNC_RESOLVERS.firefox_version()).toBeUndefined();
        });

        it('returns undefined when Firefox reports version 0 (iOS)', function () {
            window.Mozilla.Client.isFirefox = true;
            window.Mozilla.Client.FirefoxMajorVersion = 0;
            expect(ns.SYNC_RESOLVERS.firefox_version()).toBeUndefined();
        });
    });

    describe('SYNC_RESOLVERS.locale', function () {
        // <html lang> is set by Karma / browser default; save and restore
        // to avoid polluting other specs.
        let saved;
        beforeEach(function () {
            saved = document.documentElement.getAttribute('lang');
        });
        afterEach(function () {
            if (saved === null) {
                document.documentElement.removeAttribute('lang');
            } else {
                document.documentElement.setAttribute('lang', saved);
            }
        });

        it('reads <html lang>', function () {
            document.documentElement.setAttribute('lang', 'pt-BR');
            expect(ns.SYNC_RESOLVERS.locale()).toBe('pt-BR');
        });
    });

    // -------------------------------------------------------------------
    // UITOUR_EXTRACTORS
    // -------------------------------------------------------------------

    describe('UITOUR_EXTRACTORS.default_browser', function () {
        it('returns true for defaultBrowser === true', function () {
            expect(
                ns.UITOUR_EXTRACTORS.default_browser({ defaultBrowser: true })
            ).toBe(true);
        });

        it('returns false for defaultBrowser === false', function () {
            expect(
                ns.UITOUR_EXTRACTORS.default_browser({ defaultBrowser: false })
            ).toBe(false);
        });

        it('returns undefined when the field is missing', function () {
            expect(ns.UITOUR_EXTRACTORS.default_browser({})).toBeUndefined();
            expect(ns.UITOUR_EXTRACTORS.default_browser(null)).toBeUndefined();
        });
    });

    describe('UITOUR_EXTRACTORS.firefox_pinned', function () {
        it('inverts needsPin on modern Firefox (needsPin:false means pinned)', function () {
            expect(
                ns.UITOUR_EXTRACTORS.firefox_pinned({ needsPin: false })
            ).toBe(true);
            expect(
                ns.UITOUR_EXTRACTORS.firefox_pinned({ needsPin: true })
            ).toBe(false);
        });

        it('falls back to pinnedToTaskbar on older builds', function () {
            expect(
                ns.UITOUR_EXTRACTORS.firefox_pinned({ pinnedToTaskbar: true })
            ).toBe(true);
            expect(
                ns.UITOUR_EXTRACTORS.firefox_pinned({ pinnedToTaskbar: false })
            ).toBe(false);
        });

        it('falls back to `pinned` when only that field is present', function () {
            expect(ns.UITOUR_EXTRACTORS.firefox_pinned({ pinned: true })).toBe(
                true
            );
        });

        it('returns undefined when no known field is present', function () {
            expect(ns.UITOUR_EXTRACTORS.firefox_pinned({})).toBeUndefined();
            expect(ns.UITOUR_EXTRACTORS.firefox_pinned(null)).toBeUndefined();
        });
    });

    describe('UITOUR_EXTRACTORS.fxa_signed_in', function () {
        it('maps setup:true → true', function () {
            expect(ns.UITOUR_EXTRACTORS.fxa_signed_in({ setup: true })).toBe(
                true
            );
        });

        it('maps setup:false → false', function () {
            expect(ns.UITOUR_EXTRACTORS.fxa_signed_in({ setup: false })).toBe(
                false
            );
        });

        it('returns undefined for missing setup field', function () {
            expect(ns.UITOUR_EXTRACTORS.fxa_signed_in({})).toBeUndefined();
        });
    });

    describe('UITOUR_EXTRACTORS.ai_controls', function () {
        it('returns the `default` field verbatim (tri-state string enum)', function () {
            expect(
                ns.UITOUR_EXTRACTORS.ai_controls({ default: 'enabled' })
            ).toBe('enabled');
            expect(
                ns.UITOUR_EXTRACTORS.ai_controls({ default: 'available' })
            ).toBe('available');
            expect(
                ns.UITOUR_EXTRACTORS.ai_controls({ default: 'blocked' })
            ).toBe('blocked');
        });

        it('returns undefined when the field is missing', function () {
            expect(ns.UITOUR_EXTRACTORS.ai_controls({})).toBeUndefined();
        });
    });

    describe('UITOUR_EXTRACTORS.profile_age_days', function () {
        it('converts weeks to days when profileCreatedWeeksAgo is present', function () {
            expect(
                ns.UITOUR_EXTRACTORS.profile_age_days({
                    profileCreatedWeeksAgo: 4
                })
            ).toBe(28);
        });

        it('computes days from profileAgeCreated (ms epoch) when weeks unavailable', function () {
            const tenDaysAgo = Date.now() - 10 * 86400000;
            // Allow small clock drift in the assertion window (>=9, <=11).
            const days = ns.UITOUR_EXTRACTORS.profile_age_days({
                profileAgeCreated: tenDaysAgo
            });
            expect(days).toBeGreaterThanOrEqual(9);
            expect(days).toBeLessThanOrEqual(11);
        });

        it('returns undefined when neither field is present', function () {
            expect(ns.UITOUR_EXTRACTORS.profile_age_days({})).toBeUndefined();
        });
    });

    // -------------------------------------------------------------------
    // Constants surfaced for cross-checking with the Python side
    // -------------------------------------------------------------------

    describe('LAPSED_MIN_GAP', function () {
        it('equals the Python-side constant (5)', function () {
            // If this changes on either side, the lapsed_user rule fires
            // on a different population — keep them locked.
            expect(ns.LAPSED_MIN_GAP).toBe(5);
        });
    });
});
