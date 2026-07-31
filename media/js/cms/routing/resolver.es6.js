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

// Framework control params that must never be carried onto the destination — they
// would re-arm routing, re-enter the loop, or leak preview state. Mirrors the names in
// springfield/cms/routing/params.py; the active loop-breaker param is added at runtime
// from the data attribute in case a consumer overrode it.
export const RESERVED_ROUTING_PARAMS = [
    'routing',
    'routed',
    'preview_rule',
    'preview_signal'
];

/**
 * Merge inbound query params onto a destination URL so attribution (utm_*, oldversion,
 * …) survives the redirect (plan P1-1). Framework control params in `reservedParams`
 * are dropped, and a key the destination already carries is never overwritten or
 * duplicated (destination wins). Any existing query and fragment on `url` are kept.
 *
 * Client-side only — the server render stays per-request-free and CDN-cacheable.
 */
export function preserveQueryString(url, incomingSearch, reservedParams) {
    const incoming = new URLSearchParams(incomingSearch || '');
    if (Array.from(incoming.keys()).length === 0) {
        return url;
    }

    const reserved = {};
    (reservedParams || []).forEach((name) => {
        reserved[name] = true;
    });

    const hashIndex = url.indexOf('#');
    const fragment = hashIndex === -1 ? '' : url.slice(hashIndex);
    const beforeHash = hashIndex === -1 ? url : url.slice(0, hashIndex);
    const queryIndex = beforeHash.indexOf('?');
    const path =
        queryIndex === -1 ? beforeHash : beforeHash.slice(0, queryIndex);
    const existing = new URLSearchParams(
        queryIndex === -1 ? '' : beforeHash.slice(queryIndex + 1)
    );

    incoming.forEach((value, key) => {
        if (reserved[key] || existing.has(key)) {
            return; // never carry control params; destination's own value wins
        }
        existing.append(key, value);
    });

    const query = existing.toString();
    return path + (query ? '?' + query : '') + fragment;
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
    // Preview fake signals (C9), if any, resolve immediately on the client.
    const fakes = parseJSONAttribute(root, 'data-routing-fake-signals') || {};
    const canonicalUrl = root.getAttribute('data-canonical-url') || '/';
    const loopBreakerParam =
        root.getAttribute('data-loop-breaker-param') || 'routed';

    const baseOptions = opts.providerOptions || {};
    const providerOptions = {
        root: baseOptions.root,
        client: baseOptions.client,
        uiTour: baseOptions.uiTour,
        search: baseOptions.search,
        timeout: baseOptions.timeout,
        fakes: baseOptions.fakes || fakes
    };
    const provider = createProvider(manifest, providerOptions);

    // The inbound query string to carry through. Same source the URL signal reader
    // uses, so signals and preserved attribution stay consistent.
    const incomingSearch =
        baseOptions.search !== undefined
            ? baseOptions.search
            : typeof window !== 'undefined' && window.location
              ? window.location.search
              : '';
    const reservedParams = RESERVED_ROUTING_PARAMS.concat(loopBreakerParam);

    return evaluateRules(rules, provider, opts.evaluatorOptions).then(
        function (outcome) {
            onResolveOutcome(outcome);
            if (outcome.status === 'matched' && outcome.target) {
                navigate(
                    preserveQueryString(
                        outcome.target,
                        incomingSearch,
                        reservedParams
                    )
                );
            } else {
                const fallback = preserveQueryString(
                    canonicalUrl,
                    incomingSearch,
                    reservedParams
                );
                navigate(appendLoopBreaker(fallback, loopBreakerParam));
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
