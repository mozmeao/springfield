/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * User Routing — client-side resolver.
 *
 * Runs the full rule evaluator. The server does no rule matching under
 * this architecture — it just ships the resolver page with:
 *   #user-routing-rules            — array of live rules
 *   #user-routing-signal-metadata  — {signal_name: {uitour_key}} for UITour-resolved signals
 *   #user-routing-canonical-url    — fallback URL
 *   #user-routing-preview-signals  — {signal_name: value} admin overrides (empty in prod)
 *
 * Contract for a rule:
 *   { name, priority, conditions: [{signal, op, values}, ...], target_url }
 *
 * A rule matches iff every condition matches (AND). Cross-rule evaluation
 * stays OR (priority-ordered).
 *
 * Signal resolution paths:
 *   - DOM data attribute      — country
 *   - URL / <html> attributes — locale, lapsed_user
 *   - Mozilla.Client (UA)     — platform, is_firefox, firefox_version
 *   - UITour (async)          — default_browser, firefox_pinned, profile_age_days,
 *                               fxa_signed_in, ai_controls
 *
 * Optimizations:
 *   - Sync signals (DOM / UA) are resolved before any async work — most
 *     evaluations can complete instantly.
 *   - UITour is only invoked when at least one rule references a UITour-resolved
 *     signal. Pure-sync-signal rulesets never wait on UITour.
 *   - Global timeout falls back to canonical if the resolver can't decide.
 *   - Per-signal timeout for UITour so one hanging key doesn't stall the flow.
 *   - Priority-strict: a lower-priority rule can only win once every higher-priority
 *     rule has been definitively decided.
 */

(function () {
    'use strict';

    var GLOBAL_TIMEOUT_MS = 1500;
    var SIGNAL_TIMEOUT_MS = 500;
    var PING_TIMEOUT_MS = 800;

    var LAPSED_MIN_GAP = 5;

    // Tests set ``window.Mozilla.UserRoutingResolver = { autoboot: false }``
    // before this script loads to prevent the boot lifecycle from running
    // (which would read DOM blobs, mutate window.location, etc.). Pure
    // functions are still exposed on the namespace for unit-level tests.
    if (!window.Mozilla) window.Mozilla = {};
    var ns = window.Mozilla.UserRoutingResolver || {};
    window.Mozilla.UserRoutingResolver = ns;

    // -----------------------------------------------------------------------
    // Sync signal resolvers — return a value immediately, or ``undefined``
    // when the signal isn't determinable on this request. Undefined values
    // are treated as "fetched but no answer" (rule condition can't match),
    // NOT as "still pending."
    // -----------------------------------------------------------------------

    var SYNC_RESOLVERS = {
        // Server-rendered onto <html data-country-code="...">. Empty attribute
        // (no country detected server-side) → undefined.
        country: function () {
            var v = document.documentElement.getAttribute('data-country-code');
            return v ? v.toUpperCase() : undefined;
        },

        // <html lang="en-US"> — set by every Django template via LANG context.
        locale: function () {
            var v = document.documentElement.getAttribute('lang');
            return v || undefined;
        },

        // Derived: (target_version from URL path) - (oldversion from query) >= LAPSED_MIN_GAP.
        // Target version comes from the ``/whatsnew/{version}/`` URL segment.
        // ``oldversion`` accepts an optional ``rv:`` prefix (matches the shape
        // some Gecko builds emit in UA strings) — the deleted server resolver
        // stripped it, so we keep parity here.
        lapsed_user: function () {
            var pathMatch =
                window.location.pathname.match(/\/whatsnew\/(\d+)\//);
            if (!pathMatch) return undefined;
            var target = parseInt(pathMatch[1], 10);
            if (isNaN(target)) return undefined;
            var params = new window.URLSearchParams(window.location.search);
            var oldRaw = params.get('oldversion');
            if (!oldRaw) return undefined;
            var oldMatch = /^(?:rv:)?(\d{1,3})/.exec(oldRaw);
            if (!oldMatch) return undefined;
            var old = parseInt(oldMatch[1], 10);
            if (isNaN(old)) return undefined;
            return target - old >= LAPSED_MIN_GAP;
        },

        // Mozilla.Client is loaded on the resolver page via the resolver bundle
        // (see media/static-bundles.json). All Mozilla.Client sync properties
        // read navigator.userAgent + navigator.platform + Client Hints — no
        // UITour dependency, available as soon as the script loads.
        platform: function () {
            if (!window.Mozilla || !window.Mozilla.Client) return undefined;
            var p = window.Mozilla.Client.platform;
            if (!p) return undefined;
            // site.js emits ``"other"`` for unrecognized OSes; the admin
            // dropdown uses the ``"other-os"`` label from the CMS blocks
            // module. Coerce so a marketer's ``platform is other-os`` rule
            // still matches the audience the label implies.
            return p === 'other' ? 'other-os' : p;
        },
        // Note: ``is_firefox`` includes iOS Firefox (FxiOS). Mozilla.Client
        // treats FxiOS as Firefox; the deleted server resolver only matched
        // the literal string "Firefox" in the UA and excluded FxiOS. The
        // client's answer is arguably more correct — but rules that want to
        // exclude iOS should combine ``is_firefox=true`` with
        // ``platform is [osx, linux, windows, android]``.
        is_firefox: function () {
            if (!window.Mozilla || !window.Mozilla.Client) return undefined;
            // Coerce to real bool — the raw property is truthy/falsy.
            return window.Mozilla.Client.isFirefox === true;
        },
        // Guard: Mozilla.Client.FirefoxMajorVersion returns 0 (not undefined)
        // on non-Firefox and iOS Firefox UAs. Bare 0 would trip rules that
        // use ``is_not`` without an ``is_firefox`` guard, so we treat "no
        // Firefox at all" as unresolved (matching the deleted server
        // resolver's behavior).
        firefox_version: function () {
            if (!window.Mozilla || !window.Mozilla.Client) return undefined;
            if (window.Mozilla.Client.isFirefox !== true) return undefined;
            var v = window.Mozilla.Client.FirefoxMajorVersion;
            if (typeof v !== 'number' || isNaN(v) || v === 0) return undefined;
            return v;
        }
    };

    // -----------------------------------------------------------------------
    // UITour extractors — signal_name → (UITour data) → value.
    //
    // Keys here MUST match the signal names registered in
    // springfield/cms/routing/__init__.py. A signal referenced by a rule but
    // NOT present in either SYNC_RESOLVERS or UITOUR_EXTRACTORS stays
    // unresolved and its rule falls to canonical via the global timeout.
    // -----------------------------------------------------------------------

    var UITOUR_EXTRACTORS = {
        // getConfiguration('appinfo')
        default_browser: function (data) {
            if (!data || typeof data.defaultBrowser === 'undefined')
                return undefined;
            return data.defaultBrowser === true;
        },
        firefox_pinned: function (data) {
            if (!data) return undefined;
            // Firefox exposes needsPin on modern builds; older builds used
            // pinnedToTaskbar / pinned. Try all three.
            if (typeof data.needsPin !== 'undefined') {
                // needsPin is TRUE when NOT pinned — invert the semantic.
                return data.needsPin === false;
            }
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
                return Math.floor(
                    (Date.now() - data.profileAgeCreated) / 86400000
                );
            }
            return undefined;
        },

        // getConfiguration('fxa')
        fxa_signed_in: function (data) {
            if (!data || typeof data.setup === 'undefined') return undefined;
            return data.setup === true;
        },

        // getConfiguration('aiControls')
        ai_controls: function (data) {
            if (!data || typeof data.default === 'undefined') return undefined;
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
    var canonicalUrl = readJSON('user-routing-canonical-url') || '/';
    var previewSignals = readJSON('user-routing-preview-signals') || {};
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
    // Rule evaluation — tri-state, AND-within-rule, OR-across-rules
    // -----------------------------------------------------------------------

    function conditionMatches(condition, resolved) {
        var c = condition || {};
        if (!c.signal) return false;
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
        // Priority-strict: a lower-priority rule can only "win" once every
        // higher-priority rule has been definitively decided (matched or
        // not-matched). If any earlier-in-priority rule is still pending,
        // hold the decision.
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
        // Otherwise still pending — wait for more signals or global timeout.
    }

    // Collect every signal name referenced by any rule's condition. Signals
    // not referenced don't need resolving — a rule that doesn't need a
    // UITour signal shouldn't drag every user through a UITour ping.
    function collectReferencedSignals() {
        var names = {};
        for (var i = 0; i < rules.length; i++) {
            var conditions = rules[i].conditions || [];
            for (var j = 0; j < conditions.length; j++) {
                var name = conditions[j].signal;
                if (name) names[name] = true;
            }
        }
        return Object.keys(names);
    }

    // Resolve every sync signal (DOM / URL / Mozilla.Client) up front.
    // Apply preview_signal overrides on top.
    function resolveSyncSignals(referenced) {
        referenced.forEach(function (name) {
            if (SYNC_RESOLVERS[name]) {
                try {
                    resolvedSignals[name] = SYNC_RESOLVERS[name]();
                } catch (e) {
                    resolvedSignals[name] = undefined;
                }
            }
        });
        // Preview signal overrides take precedence over any resolved value.
        // Applies to sync AND UITour signals — overrides an as-yet-unresolved
        // UITour signal too, so preview URLs don't wait on UITour.
        Object.keys(previewSignals).forEach(function (name) {
            resolvedSignals[name] = previewSignals[name];
        });
    }

    // Which of the referenced signals need UITour (i.e. are UITour-only
    // signals AND haven't been overridden by preview_signal)?
    function signalsNeedingUITour(referenced) {
        return referenced.filter(function (name) {
            if (name in previewSignals) return false; // preview override — skip UITour
            if (SYNC_RESOLVERS[name]) return false; // sync-resolvable
            return name in UITOUR_EXTRACTORS;
        });
    }

    // Group UITour-required signals by their config key so we call
    // getConfiguration exactly once per key.
    function groupByUITourKey(names) {
        var byKey = {};
        names.forEach(function (name) {
            var meta = signalMetadata[name];
            var key = meta && meta.uitour_key;
            if (!key) {
                // No metadata for this signal — mark unresolved.
                resolvedSignals[name] = undefined;
                return;
            }
            if (!byKey[key]) byKey[key] = [];
            byKey[key].push(name);
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
                        resolvedSignals[name] = UITOUR_EXTRACTORS[name](data);
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
    // Expose pure functions for testing. Boot lifecycle below can be
    // skipped by setting ``ns.autoboot = false`` before this script loads.
    // -----------------------------------------------------------------------

    ns.conditionMatches = conditionMatches;
    ns.ruleMatches = ruleMatches;
    ns.evaluate = evaluate;
    ns.SYNC_RESOLVERS = SYNC_RESOLVERS;
    ns.UITOUR_EXTRACTORS = UITOUR_EXTRACTORS;
    ns.LAPSED_MIN_GAP = LAPSED_MIN_GAP;

    if (ns.autoboot === false) return;

    // -----------------------------------------------------------------------
    // Entry
    // -----------------------------------------------------------------------

    if (!rules.length) {
        done(canonicalUrl);
        return;
    }

    var referenced = collectReferencedSignals();
    resolveSyncSignals(referenced);

    // Quick pass: sync signals may already give us a definitive answer.
    onSignalUpdate();
    if (navigated) return;

    var uitourNeeded = signalsNeedingUITour(referenced);
    if (!uitourNeeded.length) {
        // Rules only need sync signals, and none of them matched (or all
        // were unresolved for other reasons). Fall back to canonical.
        done(canonicalUrl);
        return;
    }

    // UITour is required for at least one signal. Verify availability, then fetch.
    if (
        !window.Mozilla ||
        !window.Mozilla.UITour ||
        typeof window.Mozilla.UITour.ping !== 'function'
    ) {
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

    try {
        window.Mozilla.UITour.ping(function () {
            if (pingSettled) return;
            pingSettled = true;
            window.clearTimeout(pingTimer);

            setStatus('Checking your settings…');

            var byKey = groupByUITourKey(uitourNeeded);

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
