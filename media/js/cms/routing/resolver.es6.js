/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * User Routing — client resolver entrypoint (spec §7.1).
 *
 * Reads the rules and signal manifest the server rendered into data-* attributes,
 * builds the signal provider (C6), evaluates the rules (C5), and navigates: to the
 * matched rule's target on a match, or to the canonical URL with the loop-breaker
 * marker appended on no-match / timeout (spec §7.4). This is the bundled entrypoint
 * that pulls in the evaluator and readers.
 */

import { evaluateRules } from './evaluator.es6';
import { createProvider } from './readers.es6';

/**
 * No-op seam for the deferred telemetry follow-up (§4). The resolver already computes
 * the outcome (match / no-match / timeout); the follow-up attaches here without
 * reopening the resolver. Ships empty in this PR.
 */
// eslint-disable-next-line no-unused-vars
export function onResolveOutcome(outcome) {
    // Intentionally empty — telemetry follow-up will populate this.
}

function parseJSONAttribute(element, attribute) {
    try {
        return JSON.parse(element.getAttribute(attribute) || 'null');
    } catch (e) {
        return null;
    }
}

export function appendLoopBreaker(url, param) {
    const separator = url.indexOf('?') === -1 ? '?' : '&';
    return url + separator + encodeURIComponent(param) + '=1';
}

/**
 * Wire the resolver against the DOM. `options` allow injecting the root element, a
 * navigate function, and provider options (used in tests).
 */
export function initResolver(options) {
    const opts = options || {};
    const root =
        opts.root ||
        (typeof document !== 'undefined'
            ? document.querySelector('.routing-resolver')
            : null);
    if (!root) {
        return null;
    }

    const navigate =
        opts.navigate ||
        function (url) {
            window.location.assign(url);
        };

    const rules = parseJSONAttribute(root, 'data-routing-rules') || [];
    const manifest = parseJSONAttribute(root, 'data-routing-manifest') || {};
    const canonicalUrl = root.getAttribute('data-canonical-url') || '/';
    const loopBreakerParam =
        root.getAttribute('data-loop-breaker-param') || 'routed';

    const provider = createProvider(manifest, opts.providerOptions || {});

    return evaluateRules(rules, provider, opts.evaluatorOptions).then(
        function (outcome) {
            onResolveOutcome(outcome);
            if (outcome.status === 'matched' && outcome.target) {
                navigate(outcome.target);
            } else {
                navigate(appendLoopBreaker(canonicalUrl, loopBreakerParam));
            }
            return outcome;
        }
    );
}

// Auto-run when loaded as a page bundle. A no-op in contexts without the resolver
// element (e.g. unit tests import initResolver and drive it explicitly).
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initResolver();
        });
    } else {
        initResolver();
    }
}
