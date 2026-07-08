/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Prototype 1 for the WNP Dynamic Rendering plan.
 *
 * Measures UITour timing on the page and POSTs the numbers to
 * /whatsnew/dispatch/timing-test/report/. Reveals the same numbers in a small
 * on-page table so a dogfood tester can see what was measured.
 *
 * Sends only timings and success/failure flags. Never sends state values
 * (default browser bool, AI controls string, etc.).
 */

(function () {
    'use strict';

    // Relative URL — resolves against the page location, which lives at
    // /{locale}/whatsnew/dispatch/timing-test/. Yields the locale-prefixed
    // /{locale}/whatsnew/dispatch/timing-test/report/ endpoint.
    var REPORT_URL = 'report/';

    // Deliberately generous so we can see the P95/P99 tail.
    var PING_TIMEOUT_MS = 2000;
    // Phase-level fallback: if getConfiguration() never calls back for any
    // key, report partial results after this window rather than hanging.
    // Every UITour phase must have a bounded worst case.
    var CONFIG_TIMEOUT_MS = 3000;

    var results = {
        ping_ms: null,
        ping_success: false,
        appinfo_ms: null,
        appinfo_success: false,
        sync_ms: null,
        sync_success: false,
        total_ms: null,
        outcome: 'unknown'
    };

    var start = performance.now();

    function elapsed() {
        return Math.round(performance.now() - start);
    }

    function setStatus(text) {
        var status = document.getElementById('timing-test-status');
        if (status) {
            status.textContent = text;
        }
    }

    function renderResults() {
        var body = document.getElementById('timing-test-results-body');
        if (!body) {
            return;
        }
        body.innerHTML = '';
        var rows = [
            [
                'UITour ping',
                results.ping_success
                    ? results.ping_ms + ' ms'
                    : 'failed or unavailable'
            ],
            [
                'getConfiguration(appinfo)',
                results.appinfo_success ? results.appinfo_ms + ' ms' : '—'
            ],
            [
                'getConfiguration(sync)',
                results.sync_success ? results.sync_ms + ' ms' : '—'
            ],
            ['Total elapsed', results.total_ms + ' ms'],
            ['Outcome', results.outcome]
        ];
        rows.forEach(function (row) {
            var tr = document.createElement('tr');
            var td1 = document.createElement('td');
            var td2 = document.createElement('td');
            td1.textContent = row[0];
            td2.textContent = row[1];
            tr.appendChild(td1);
            tr.appendChild(td2);
            body.appendChild(tr);
        });
        var resultsEl = document.getElementById('timing-test-results');
        if (resultsEl) {
            resultsEl.hidden = false;
        }
    }

    function report() {
        results.total_ms = elapsed();
        setStatus('Measurement complete.');
        renderResults();
        try {
            fetch(REPORT_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(results),
                keepalive: true
            })
                .then(function () {
                    var thanks = document.getElementById('timing-test-thanks');
                    if (thanks) {
                        thanks.hidden = false;
                    }
                })
                .catch(function () {
                    // Fine — the on-page table still shows results.
                });
        } catch (e) {
            // Ignore — nothing more we can do.
        }
    }

    // Bail early if UITour isn't available at all.
    if (
        !window.Mozilla ||
        !window.Mozilla.UITour ||
        typeof window.Mozilla.UITour.ping !== 'function'
    ) {
        results.outcome = 'no_uitour';
        setStatus('UITour is not available on this browser.');
        report();
        return;
    }

    var pingResolved = false;
    var pingStart = performance.now();

    var pingTimer = window.setTimeout(function () {
        if (pingResolved) {
            return;
        }
        pingResolved = true;
        results.ping_ms = Math.round(performance.now() - pingStart);
        results.ping_success = false;
        results.outcome = 'ping_timeout';
        report();
    }, PING_TIMEOUT_MS);

    setStatus('Waiting for UITour ping…');

    window.Mozilla.UITour.ping(function () {
        if (pingResolved) {
            return;
        }
        pingResolved = true;
        window.clearTimeout(pingTimer);
        results.ping_ms = Math.round(performance.now() - pingStart);
        results.ping_success = true;

        setStatus('Fetching getConfiguration values…');

        var appinfoStart = performance.now();
        var syncStart = performance.now();
        var configReported = false;
        var pending = 2;
        var anyFailed = false;

        function finalize(reason) {
            if (configReported) {
                return;
            }
            configReported = true;
            window.clearTimeout(configTimer);
            if (reason === 'timeout') {
                results.outcome = 'config_timeout';
            } else {
                results.outcome = anyFailed ? 'config_error' : 'success';
            }
            report();
        }

        function checkDone() {
            if (pending === 0) {
                finalize('done');
            }
        }

        // Bounded worst case for the whole config phase.
        var configTimer = window.setTimeout(function () {
            // Whichever key didn't respond stays with success=false and
            // ms=null in the payload; the outcome makes the reason explicit.
            finalize('timeout');
        }, CONFIG_TIMEOUT_MS);

        try {
            window.Mozilla.UITour.getConfiguration('appinfo', function (data) {
                if (configReported) {
                    return;
                }
                results.appinfo_ms = Math.round(
                    performance.now() - appinfoStart
                );
                // Note: we check for a truthy object here, but we do NOT
                // send any of its values back to the server. Only timing
                // and success/failure.
                results.appinfo_success = !!data;
                if (!data) {
                    anyFailed = true;
                }
                pending -= 1;
                checkDone();
            });
        } catch (e) {
            results.appinfo_ms = Math.round(performance.now() - appinfoStart);
            results.appinfo_success = false;
            anyFailed = true;
            pending -= 1;
            checkDone();
        }

        try {
            window.Mozilla.UITour.getConfiguration('sync', function (data) {
                if (configReported) {
                    return;
                }
                results.sync_ms = Math.round(performance.now() - syncStart);
                // sync may return an object even when the user is signed
                // out — that's a successful call, not a failure.
                results.sync_success = data !== undefined;
                pending -= 1;
                checkDone();
            });
        } catch (e) {
            results.sync_ms = Math.round(performance.now() - syncStart);
            results.sync_success = false;
            anyFailed = true;
            pending -= 1;
            checkDone();
        }
    });
})();
