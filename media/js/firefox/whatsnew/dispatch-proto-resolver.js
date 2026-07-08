/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Prototype 2 — client-side resolver library + rule evaluator.
 *
 * Reads the embedded rules JSON, calls UITour with per-signal timeouts,
 * evaluates rules as signals resolve, short-circuits to the first matching
 * variant. Falls back to canonical if nothing matches (or a global timeout
 * elapses).
 *
 * Sends no state values off the client — the navigation itself is the only
 * observable side effect.
 */

(function () {
    'use strict';

    // -----------------------------------------------------------------------
    // Config / constants
    // -----------------------------------------------------------------------

    // Global upper bound. If we haven't decided by this many milliseconds we
    // give up and navigate to canonical rather than leaving the user stuck.
    var GLOBAL_TIMEOUT_MS = 1500;

    // Per-signal upper bound. If a single UITour key doesn't respond within
    // this window, we treat it as "unknown" and move on. Some keys are known
    // to hang on some Firefox versions (see prototype 1 findings).
    var SIGNAL_TIMEOUT_MS = 500;

    // UITour ping's own timeout. Cheap in practice (~2ms in prototype 1) but
    // we bound it anyway.
    var PING_TIMEOUT_MS = 800;

    // Map from signal name (used in rules) to the UITour getConfiguration key
    // and a value extractor. If a future signal comes from somewhere other
    // than UITour, its entry here can just point at a different source.
    var SIGNAL_RESOLVERS = {
        sync_setup: {
            uitour_key: 'sync',
            extract: function (data) {
                // Nimbus/UITour returns { setup: true|false, mobileDevices: n, ... }.
                // A missing 'setup' key on this Firefox version is treated as unknown.
                if (!data || typeof data.setup === 'undefined') {
                    return undefined;
                }
                return data.setup === true;
            }
        }
        // If we later need default_browser, add:
        //   default_browser: { uitour_key: 'appinfo',
        //                      extract: d => d && d.defaultBrowser === true }
    };

    // -----------------------------------------------------------------------
    // Bootstrap
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

    function readText(id) {
        var node = document.getElementById(id);
        return node ? node.textContent.trim() : '';
    }

    var rules = readJSON('proto-rules-data') || [];
    var canonicalUrl = readText('proto-canonical-url');
    var status = document.getElementById('proto-resolver-status');

    function setStatus(text) {
        if (status) status.textContent = text;
    }

    // -----------------------------------------------------------------------
    // Navigation — every code path ends here exactly once.
    // -----------------------------------------------------------------------

    var navigated = false;
    function navigate(url) {
        if (navigated) return;
        navigated = true;
        setStatus('Redirecting…');
        // Prefer replace so the resolver URL doesn't clutter history.
        try {
            window.location.replace(url);
        } catch (e) {
            window.location.href = url;
        }
    }

    // Global fallback timer — if nothing else has fired by now, go canonical.
    var globalTimer = window.setTimeout(function () {
        navigate(canonicalUrl);
    }, GLOBAL_TIMEOUT_MS);

    function done(url) {
        window.clearTimeout(globalTimer);
        navigate(url);
    }

    // -----------------------------------------------------------------------
    // Rule evaluation
    // -----------------------------------------------------------------------

    // Check a single rule against the signal map. Returns:
    //   true  → matched (this rule's variant should be served)
    //   false → definitively did not match
    //   null  → cannot decide yet (a required signal is not resolved)
    function ruleMatches(rule, resolved) {
        var c = rule.condition;
        if (!(c.signal in resolved)) {
            return null;
        }
        var v = resolved[c.signal];
        if (v === undefined) {
            // Signal is 'known unknown' — resolver returned undefined.
            return null;
        }
        return v === c.equals;
    }

    // Evaluate the whole ruleset. Returns:
    //   { matched: rule } if some rule matched
    //   { definitively_none: true } if every rule definitively failed
    //   { pending: true } if any rule is still undecidable
    function evaluate(resolved) {
        var pending = false;
        // Sorted client-side by priority for determinism, though the server
        // already ordered rules on the way out.
        rules.sort(function (a, b) {
            return a.priority - b.priority;
        });
        for (var i = 0; i < rules.length; i++) {
            var rule = rules[i];
            var m = ruleMatches(rule, resolved);
            if (m === true) return { matched: rule };
            if (m === null) pending = true;
        }
        if (pending) return { pending: true };
        return { definitively_none: true };
    }

    function targetForVariant(variant) {
        // Rule targets are variant slugs; the server tells us where canonical
        // lives, and the variants are siblings under the same version path.
        return canonicalUrl.replace(/canonical\/$/, variant + '/');
    }

    // -----------------------------------------------------------------------
    // Signal fetching
    // -----------------------------------------------------------------------

    var resolvedSignals = {};

    // Called each time a signal resolves (either with a value or as unknown).
    // Re-evaluates rules and either navigates or waits for more signals.
    function onSignalUpdate() {
        var result = evaluate(resolvedSignals);
        if (result.matched) {
            done(targetForVariant(result.matched.variant));
        } else if (result.definitively_none) {
            done(canonicalUrl);
        }
        // Otherwise still pending — wait for more signals or the global timeout.
    }

    // Determine which signal names any rule needs, deduplicated.
    function requiredSignalNames() {
        var seen = {};
        var out = [];
        rules.forEach(function (rule) {
            (rule.required_signals || []).forEach(function (name) {
                if (!seen[name]) {
                    seen[name] = true;
                    out.push(name);
                }
            });
        });
        return out;
    }

    // Group signals by their underlying UITour key so we only call
    // getConfiguration(key) once per key even if multiple signals derive
    // from the same data.
    function groupByUITourKey(signalNames) {
        var byKey = {};
        signalNames.forEach(function (name) {
            var resolver = SIGNAL_RESOLVERS[name];
            if (!resolver) {
                // No resolver registered — mark as unknown so it doesn't block us.
                resolvedSignals[name] = undefined;
                return;
            }
            if (!byKey[resolver.uitour_key]) {
                byKey[resolver.uitour_key] = [];
            }
            byKey[resolver.uitour_key].push({
                name: name,
                extract: resolver.extract
            });
        });
        return byKey;
    }

    function fetchUITourKey(key, consumers) {
        var settled = false;
        var timer = window.setTimeout(function () {
            if (settled) return;
            settled = true;
            // Per-signal timeout — mark all consumers as unknown.
            consumers.forEach(function (c) {
                if (!(c.name in resolvedSignals)) {
                    resolvedSignals[c.name] = undefined;
                }
            });
            onSignalUpdate();
        }, SIGNAL_TIMEOUT_MS);

        try {
            window.Mozilla.UITour.getConfiguration(key, function (data) {
                if (settled) return;
                settled = true;
                window.clearTimeout(timer);
                consumers.forEach(function (c) {
                    var value;
                    try {
                        value = c.extract(data);
                    } catch (e) {
                        value = undefined;
                    }
                    resolvedSignals[c.name] = value;
                });
                onSignalUpdate();
            });
        } catch (e) {
            if (settled) return;
            settled = true;
            window.clearTimeout(timer);
            consumers.forEach(function (c) {
                resolvedSignals[c.name] = undefined;
            });
            onSignalUpdate();
        }
    }

    // -----------------------------------------------------------------------
    // Entry point
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
        // UITour not available at all — every signal is unknown. Rules with
        // unknown signals fall through to canonical.
        done(canonicalUrl);
        return;
    }

    setStatus('Contacting Firefox…');

    var pingSettled = false;
    var pingTimer = window.setTimeout(function () {
        if (pingSettled) return;
        pingSettled = true;
        // Ping timed out — no getConfiguration can be trusted. Canonical.
        done(canonicalUrl);
    }, PING_TIMEOUT_MS);

    window.Mozilla.UITour.ping(function () {
        if (pingSettled) return;
        pingSettled = true;
        window.clearTimeout(pingTimer);

        setStatus('Checking your settings…');

        var byKey = groupByUITourKey(requiredSignalNames());

        // If groupByUITourKey resolved everything as unknown up front, we
        // may already be able to decide.
        onSignalUpdate();
        if (navigated) return;

        // Otherwise fetch each UITour key.
        Object.keys(byKey).forEach(function (key) {
            fetchUITourKey(key, byKey[key]);
        });
    });
})();
