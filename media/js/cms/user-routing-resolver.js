/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * User Routing — client-side resolver library.
 *
 * Reads three JSON blobs embedded in the resolver page (all three are
 * application/json script elements — they must survive HTML autoescape
 * cleanly, so the server pre-escapes </-sequences too):
 *   #user-routing-rules            — array of rules the client must evaluate
 *   #user-routing-signal-metadata  — {signal_name: {uitour_key}} for required signals
 *   #user-routing-canonical-url    — fallback URL string
 *
 * Contract for a rule:
 *   { name, priority, conditions: [{signal, op, values}, ...], target_url }
 *
 * A rule contains one or more conditions joined by AND — the rule matches
 * only when every condition matches. Cross-rule evaluation stays OR
 * (priority-ordered).
 *
 * Contract for signal metadata:
 *   { <signal_name>: { uitour_key: '<key>' } }
 *
 * The client-side EXTRACTORS map (below) knows how to turn a UITour
 * getConfiguration payload into a signal value for each supported signal.
 * Signal names here match the entries in springfield.cms.routing.__init__.
 *
 * Timing model:
 *   - Global timeout: fall back to canonical if we can't decide overall.
 *   - Per-signal timeout: one hanging UITour key doesn't stall the resolver.
 *   - Short-circuit: navigate as soon as a rule fully matches, even if
 *     other signals are still resolving.
 */

(function () {
    'use strict';

    // Tuning — matches the plan doc's design budget.
    // Global upper bound before the resolver gives up and falls back to canonical.
    var GLOBAL_TIMEOUT_MS = 1500;

    // Per-signal upper bound. Some UITour keys have been observed to hang on
    // certain Firefox builds; a bounded worst case protects the whole flow.
    var SIGNAL_TIMEOUT_MS = 500;

    // UITour ping timeout. Cheap in practice (~2ms) but must be bounded.
    var PING_TIMEOUT_MS = 800;

    // -----------------------------------------------------------------------
    // Extractors: signal_name → (UITour data) → value
    //
    // Keys here MUST match the signal names registered in
    // springfield/cms/routing/__init__.py. If a rule references a signal
    // that isn't in this map, its value stays undefined and the rule is
    // treated as unresolved (and thus falls to canonical via the global
    // timeout).
    // -----------------------------------------------------------------------
    var EXTRACTORS = {
        // From getConfiguration('appinfo')
        default_browser: function (data) {
            if (!data || typeof data.defaultBrowser === 'undefined')
                return undefined;
            return data.defaultBrowser === true;
        },
        firefox_pinned: function (data) {
            if (!data) return undefined;
            // Different Firefox versions expose the pin state under different
            // keys — try the ones we've seen in the wild.
            if (typeof data.pinnedToTaskbar !== 'undefined') {
                return data.pinnedToTaskbar === true;
            }
            if (typeof data.pinned !== 'undefined') {
                return data.pinned === true;
            }
            return undefined;
        },
        profile_age_days: function (data) {
            if (!data) return undefined;
            if (typeof data.profileCreatedWeeksAgo === 'number') {
                return data.profileCreatedWeeksAgo * 7;
            }
            if (typeof data.profileAgeCreated === 'number') {
                // Milliseconds since epoch → days ago.
                return Math.floor(
                    (Date.now() - data.profileAgeCreated) / 86400000
                );
            }
            return undefined;
        },

        // From getConfiguration('fxa')
        fxa_signed_in: function (data) {
            if (!data || typeof data.setup === 'undefined') return undefined;
            return data.setup === true;
        },

        // From getConfiguration('aiControls')
        ai_controls: function (data) {
            // Consistent typeof guard (like the other extractors) — using
            // `data.default || undefined` would coerce any legitimate falsy
            // value ('', false, 0) to undefined and mask real answers.
            if (!data || typeof data.default === 'undefined') {
                return undefined;
            }
            // The tri-state that ships today: 'enabled' | 'available' | 'blocked'.
            return data.default;
        }
    };

    // -----------------------------------------------------------------------
    // Boot: read embedded data
    // -----------------------------------------------------------------------

    function readJSON(id) {
        var node = document.getElementById(id);
        if (!node) return null;
        try {
            return JSON.parse(node.textContent);
        } catch (e) {
            return null;
        }
    }

    var rules = readJSON('user-routing-rules') || [];
    var signalMetadata = readJSON('user-routing-signal-metadata') || {};
    // Canonical URL is emitted as a JSON string so the server-side escape
    // path is the same for all three blobs and & doesn't get autoescaped.
    // Fall back to the site root if the blob is missing or unparseable —
    // never navigate('') which would reload the same URL and loop.
    var canonicalUrl = readJSON('user-routing-canonical-url') || '/';
    var status = document.getElementById('user-routing-status');

    function setStatus(text) {
        if (status) status.textContent = text;
    }

    // -----------------------------------------------------------------------
    // Navigation — every code path ends here at most once
    // -----------------------------------------------------------------------

    var navigated = false;
    function navigate(url) {
        if (navigated) return;
        navigated = true;
        setStatus('Redirecting…');
        try {
            window.location.replace(url);
        } catch (e) {
            window.location.href = url;
        }
    }

    var globalTimer = window.setTimeout(function () {
        navigate(canonicalUrl);
    }, GLOBAL_TIMEOUT_MS);

    function done(url) {
        window.clearTimeout(globalTimer);
        navigate(url);
    }

    // -----------------------------------------------------------------------
    // Rule evaluation
    //
    // Condition shape (matches the server-side dispatcher's serialization):
    //   { signal: '<name>', op: 'is' | 'is_not', values: [<v1>, <v2>, ...] }
    //
    // Rule shape:
    //   { conditions: [<condition>, ...], ... }
    //
    // A rule matches iff every condition matches (AND). Per-condition
    // tri-state combines as:
    //   any false     → rule is false (short-circuit — one failing AND-clause
    //                    is enough to reject, regardless of unresolved others)
    //   else any null → rule is null (need to wait for more signals)
    //   else          → rule is true
    //
    // conditionMatches / ruleMatches both return:
    //   true  → matched
    //   false → definitively did not match
    //   null  → cannot decide yet (signal unresolved)
    // -----------------------------------------------------------------------

    function conditionMatches(condition, resolved) {
        var c = condition || {};
        if (!c.signal) return false;
        // Distinguish 'signal not fetched yet' from 'fetched but no value':
        //   not in resolved                → null   (still pending)
        //   in resolved but value=undefined → false (fetched and failed;
        //                                           condition can't match)
        if (!(c.signal in resolved)) return null;
        var v = resolved[c.signal];
        if (typeof v === 'undefined') return false;
        var values = c.values || [];
        if (!values.length) return false;
        var isInList = values.indexOf(v) !== -1;
        var op = c.op || 'is';
        if (op === 'is') return isInList;
        if (op === 'is_not') return !isInList;
        return false;
    }

    function ruleMatches(rule, resolved) {
        var conditions = rule.conditions || [];
        if (!conditions.length) return false;
        var anyPending = false;
        for (var i = 0; i < conditions.length; i++) {
            var outcome = conditionMatches(conditions[i], resolved);
            if (outcome === false) return false;
            if (outcome === null) anyPending = true;
        }
        if (anyPending) return null;
        return true;
    }

    function evaluate(resolved) {
        // Priority requires strict ordering: a lower-priority rule can
        // only "win" once every higher-priority rule has been definitively
        // decided (matched or not-matched). If any earlier-in-priority
        // rule is still pending, we hold the decision — otherwise a slow
        // signal on rule A could let rule B claim traffic that A would
        // have taken as soon as its signal resolved.
        var pending = false;
        rules.sort(function (a, b) {
            return (a.priority || 0) - (b.priority || 0);
        });
        for (var i = 0; i < rules.length; i++) {
            var m = ruleMatches(rules[i], resolved);
            if (m === true) {
                if (pending) return { pending: true };
                return { matched: rules[i] };
            }
            if (m === null) pending = true;
        }
        if (pending) return { pending: true };
        return { definitively_none: true };
    }

    // -----------------------------------------------------------------------
    // Signal resolution
    // -----------------------------------------------------------------------

    var resolvedSignals = {};

    function onSignalUpdate() {
        var result = evaluate(resolvedSignals);
        if (result.matched) {
            done(result.matched.target_url);
        } else if (result.definitively_none) {
            done(canonicalUrl);
        }
        // Otherwise still pending — wait for more signals or the global timeout.
    }

    // Group required signals by their UITour key so we call getConfiguration
    // exactly once per key even if multiple signals derive from the same
    // underlying data.
    function groupByUITourKey() {
        var byKey = {};
        Object.keys(signalMetadata).forEach(function (signalName) {
            if (!EXTRACTORS[signalName]) {
                // No extractor registered — signal stays unresolved.
                resolvedSignals[signalName] = undefined;
                return;
            }
            var uitourKey = signalMetadata[signalName].uitour_key;
            if (!uitourKey) {
                resolvedSignals[signalName] = undefined;
                return;
            }
            if (!byKey[uitourKey]) byKey[uitourKey] = [];
            byKey[uitourKey].push(signalName);
        });
        return byKey;
    }

    function fetchUITourKey(key, signalNames) {
        var settled = false;
        var timer = window.setTimeout(function () {
            if (settled) return;
            settled = true;
            signalNames.forEach(function (name) {
                if (!(name in resolvedSignals))
                    resolvedSignals[name] = undefined;
            });
            onSignalUpdate();
        }, SIGNAL_TIMEOUT_MS);

        try {
            window.Mozilla.UITour.getConfiguration(key, function (data) {
                if (settled) return;
                settled = true;
                window.clearTimeout(timer);
                signalNames.forEach(function (name) {
                    try {
                        resolvedSignals[name] = EXTRACTORS[name](data);
                    } catch (e) {
                        resolvedSignals[name] = undefined;
                    }
                });
                onSignalUpdate();
            });
        } catch (e) {
            if (settled) return;
            settled = true;
            window.clearTimeout(timer);
            signalNames.forEach(function (name) {
                resolvedSignals[name] = undefined;
            });
            onSignalUpdate();
        }
    }

    // -----------------------------------------------------------------------
    // Entry
    // -----------------------------------------------------------------------

    if (!rules.length) {
        done(canonicalUrl);
        return;
    }

    if (
        !window.Mozilla ||
        !window.Mozilla.UITour ||
        typeof window.Mozilla.UITour.ping !== 'function'
    ) {
        // UITour not exposed on this browser (non-Firefox, or not on the
        // allowlisted origin). Every client-side rule is unresolvable →
        // fall back to canonical.
        done(canonicalUrl);
        return;
    }

    setStatus('Contacting Firefox…');

    var pingSettled = false;
    var pingTimer = window.setTimeout(function () {
        if (pingSettled) return;
        pingSettled = true;
        done(canonicalUrl);
    }, PING_TIMEOUT_MS);

    // Wrap ping() the same way fetchUITourKey wraps getConfiguration —
    // a synchronous throw (e.g. UITour present but origin not allowlisted
    // for this call) shouldn't escape the IIFE. The pingTimer will still
    // fire eventually, so we don't need to signal completion here; just
    // avoid the console noise from an uncaught error.
    try {
        window.Mozilla.UITour.ping(function () {
            if (pingSettled) return;
            pingSettled = true;
            window.clearTimeout(pingTimer);

            setStatus('Checking your settings…');

            var byKey = groupByUITourKey();

            // A quick pass in case groupByUITourKey resolved everything as
            // unknown up front — we may already have enough to decide.
            onSignalUpdate();
            if (navigated) return;

            Object.keys(byKey).forEach(function (key) {
                fetchUITourKey(key, byKey[key]);
            });
        });
    } catch (e) {
        if (pingSettled) return;
        pingSettled = true;
        window.clearTimeout(pingTimer);
        done(canonicalUrl);
    }
})();
