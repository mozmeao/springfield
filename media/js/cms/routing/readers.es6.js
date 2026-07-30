/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * User Routing — client signal-reader adapters (spec §4.2).
 *
 * This is the reader seam (plan §0.4-B): every Firefox/Mozilla-specific read —
 * Mozilla.Client, UITour, the server-rendered geo attribute — lives here, so the
 * evaluator core (C5) stays generic. Each adapter implements a `read(descriptor)`
 * returning a Promise that resolves to the signal's value, or rejects when the value
 * is unavailable (which the evaluator treats as not-matched).
 *
 * `createProvider(manifest, options)` composes the four adapters into the provider the
 * evaluator consumes. The manifest (signal name -> {source, browserStateKey, valueType})
 * is serialized server-side from the Python registry and delivered on the resolver
 * page (C8); all Firefox/Mozilla globals are injectable for testing.
 */

import {
    PER_SIGNAL_TIMEOUT_MS,
    PER_UITOUR_KEY_TIMEOUT_MS
} from './evaluator.es6';

// Source identifiers, mirroring the Python Source enum values (C1).
export const SOURCE_CDN_GEO = 'cdn_geo';
export const SOURCE_USER_AGENT = 'user_agent';
export const SOURCE_UITOUR = 'uitour';
export const SOURCE_URL = 'url';

function mozillaGlobal() {
    return typeof window !== 'undefined' && window.Mozilla
        ? window.Mozilla
        : null;
}

/**
 * CDN geo — country is server-rendered into `data-country-code` on <html>, since the
 * client cannot read the CDN header directly (spec §4.2). Injectable `root` element.
 */
export function createGeoReader(options) {
    const opts = options || {};
    const root =
        opts.root ||
        (typeof document !== 'undefined' ? document.documentElement : null);
    return {
        read: function () {
            return new Promise(function (resolve, reject) {
                if (!root || !root.dataset) {
                    reject();
                    return;
                }
                const value = root.dataset.countryCode;
                if (value) {
                    resolve(value);
                } else {
                    reject();
                }
            });
        }
    };
}

/**
 * User-Agent — read via Mozilla.Client, the canonical UA parser (spec §4.2). Its UA
 * methods work in any browser (returning falsey off Firefox), so it is not Firefox-
 * gated. Injectable `client`.
 */
export function createUserAgentReader(options) {
    const opts = options || {};
    const client =
        opts.client || (mozillaGlobal() ? mozillaGlobal().Client : null);
    return {
        read: function (descriptor) {
            return new Promise(function (resolve, reject) {
                if (!client) {
                    reject();
                    return;
                }
                if (descriptor.name === 'is_firefox') {
                    // A real boolean — false off Firefox (still an available value).
                    resolve(!!client.isFirefox);
                    return;
                }
                if (descriptor.name === 'platform') {
                    if (client.platform) {
                        resolve(client.platform);
                    } else {
                        reject();
                    }
                    return;
                }
                if (descriptor.name === 'firefox_version') {
                    const version =
                        typeof client._getFirefoxVersion === 'function'
                            ? client._getFirefoxVersion()
                            : client.FirefoxVersion;
                    // Empty off Firefox -> unavailable, so version rules don't misfire.
                    if (version) {
                        resolve(version);
                    } else {
                        reject();
                    }
                    return;
                }
                reject();
            });
        }
    };
}

// Per-signal extraction from a UITour getConfiguration() payload. Firefox-specific and
// therefore quarantined here. NOTE: the exact fields for `profile_age` and
// `ai_controls` are provisional and need validating against a real Firefox UITour.
const UITOUR_EXTRACTORS = {
    is_default_browser: function (config) {
        return config.defaultBrowser;
    },
    fxa_signed_in: function (config) {
        return config.setup;
    },
    profile_age: function (config) {
        return typeof config.profileCreatedWeeks === 'number'
            ? config.profileCreatedWeeks * 7
            : undefined;
    },
    ai_controls: function (config) {
        return config.state;
    }
};

/**
 * UITour — Firefox-only browser state, read via a ping-gated getConfiguration under a
 * per-key budget (spec §4.2, §7.5). A ping or getConfiguration that never answers
 * leaves the read pending until the budget expires, then rejects (⇒ not-matched).
 * Injectable `uiTour` and `timeout`.
 */
export function createUITourReader(options) {
    const opts = options || {};
    const uiTour =
        opts.uiTour || (mozillaGlobal() ? mozillaGlobal().UITour : null);
    const timeout = opts.timeout || PER_UITOUR_KEY_TIMEOUT_MS;
    return {
        read: function (descriptor) {
            return new Promise(function (resolve, reject) {
                const extractor = UITOUR_EXTRACTORS[descriptor.name];
                if (
                    !uiTour ||
                    typeof uiTour.getConfiguration !== 'function' ||
                    typeof uiTour.ping !== 'function' ||
                    !descriptor.browserStateKey ||
                    !extractor
                ) {
                    reject();
                    return;
                }
                let settled = false;
                const timer = window.setTimeout(function () {
                    if (!settled) {
                        settled = true;
                        reject();
                    }
                }, timeout);
                uiTour.ping(function () {
                    if (settled) {
                        return;
                    }
                    uiTour.getConfiguration(
                        descriptor.browserStateKey,
                        function (config) {
                            if (settled) {
                                return;
                            }
                            settled = true;
                            window.clearTimeout(timer);
                            const value = extractor(config || {});
                            if (value === undefined || value === null) {
                                reject();
                            } else {
                                resolve(value);
                            }
                        }
                    );
                });
            });
        }
    };
}

/**
 * URL — a signal named after a query param, read from the current URL (spec §4.2).
 * Injectable `search` string.
 */
export function createUrlReader(options) {
    const opts = options || {};
    const search =
        opts.search === undefined
            ? typeof window !== 'undefined'
                ? window.location.search
                : ''
            : opts.search;
    const params = new URLSearchParams(search);
    return {
        read: function (descriptor) {
            return new Promise(function (resolve, reject) {
                if (params.has(descriptor.name)) {
                    resolve(params.get(descriptor.name));
                } else {
                    reject();
                }
            });
        }
    };
}

/**
 * Compose the four adapters into the provider the evaluator (C5) consumes.
 *
 * @param manifest signal name -> { source, browserStateKey?, valueType? }
 * @param options  injected dependencies passed through to each adapter (root, client,
 *                 uiTour, search, timeout).
 */
export function createProvider(manifest, options) {
    const signalManifest = manifest || {};
    const readers = {};
    readers[SOURCE_CDN_GEO] = createGeoReader(options);
    readers[SOURCE_USER_AGENT] = createUserAgentReader(options);
    readers[SOURCE_UITOUR] = createUITourReader(options);
    readers[SOURCE_URL] = createUrlReader(options);

    function descriptorFor(name) {
        const entry = signalManifest[name];
        if (!entry) {
            return null;
        }
        return {
            name: name,
            source: entry.source,
            browserStateKey: entry.browserStateKey,
            valueType: entry.valueType
        };
    }

    return {
        read: function (name) {
            const descriptor = descriptorFor(name);
            if (!descriptor) {
                return Promise.reject();
            }
            const reader = readers[descriptor.source];
            if (!reader) {
                return Promise.reject();
            }
            return reader.read(descriptor);
        },
        getBudgetMs: function (name) {
            const descriptor = descriptorFor(name);
            if (descriptor && descriptor.source === SOURCE_UITOUR) {
                return PER_UITOUR_KEY_TIMEOUT_MS;
            }
            return PER_SIGNAL_TIMEOUT_MS;
        }
    };
}
