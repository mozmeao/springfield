/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * User Routing — client signal-reader adapters.
 *
 * This is the reader seam: every Firefox/Mozilla-specific read —
 * Mozilla.Client, UITour, the server-rendered geo attribute — lives here, so the
 * evaluator core stays generic. Each adapter implements a `read(descriptor)`
 * returning a Promise that resolves to the signal's value, or rejects when the value
 * is unavailable (which the evaluator treats as not-matched).
 *
 * `createProvider(manifest, options)` composes the four adapters into the provider the
 * evaluator consumes. The manifest (signal name -> {source, browserStateKey, valueType})
 * is serialized server-side from the Python registry and delivered on the resolver
 * page; all Firefox/Mozilla globals are injectable for testing.
 */

import {
    PER_SIGNAL_TIMEOUT_MS,
    PER_UITOUR_KEY_TIMEOUT_MS,
    normalizeVersion
} from './evaluator.es6';
import { detectBrowser, isBrave } from '../components/flare-browser-detect.es6';

// Source identifiers, mirroring the Python Source enum values.
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
 * A locale/language tag reduced to its base language subtag: `en-US` -> `en`.
 * Lowercased because browsers are inconsistent about tag casing, while the base
 * subtag is always lowercase in the value list authors pick from.
 */
export function baseLanguage(tag) {
    return String(tag || '')
        .split('-')[0]
        .toLowerCase();
}

/**
 * CDN geo — country is server-rendered into `data-country-code` on <html>, since the
 * client cannot read the CDN header directly. Injectable `root` element.
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
 * User-Agent — read via Mozilla.Client, the canonical UA parser. Its UA
 * methods work in any browser (returning falsey off Firefox), so it is not Firefox-
 * gated. Injectable `client`, `navigator`, and `isBrave`.
 */
export function createUserAgentReader(options) {
    const opts = options || {};
    const client =
        opts.client || (mozillaGlobal() ? mozillaGlobal().Client : null);
    const nav =
        opts.navigator || (typeof navigator !== 'undefined' ? navigator : null);
    const detectBraveBrowser = opts.isBrave || isBrave;
    return {
        read: function (descriptor) {
            return new Promise(function (resolve, reject) {
                if (descriptor.name === 'browser_language') {
                    // Checked before the Mozilla.Client guard below: this is a plain
                    // browser API, available off Firefox too. Only the top preference is
                    // read — the ordered list would need list-valued signal support the
                    // evaluator does not have.
                    const preferred =
                        nav &&
                        ((nav.languages && nav.languages[0]) || nav.language);
                    if (preferred) {
                        resolve(baseLanguage(preferred));
                    } else {
                        reject();
                    }
                    return;
                }
                if (descriptor.name === 'browser_name') {
                    // Also checked before the Mozilla.Client guard: this is UA sniffing,
                    // available off Firefox too. Brave reports Chrome's user agent
                    // verbatim, so it's only worth the extra async API check when UA
                    // detection lands on Chrome — every other result is unambiguous.
                    if (!nav || !nav.userAgent) {
                        reject();
                        return;
                    }
                    const detected = detectBrowser(nav.userAgent);
                    if (detected !== 'chrome') {
                        resolve(detected);
                        return;
                    }
                    detectBraveBrowser().then(function (brave) {
                        resolve(brave ? 'brave' : 'chrome');
                    });
                    return;
                }
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

/**
 * Collapse UITour's per-feature AI control states into one posture.
 *
 * `aiControls` reports a state per AI feature (`translations`, `sidebarChatbot`, …) plus a
 * `default` master, with no overall summary. Iterating whatever keys arrive — rather than
 * naming features — means a new Firefox AI feature folds in without a change here.
 *
 * `available` counts as no choice: per Firefox's own wording it means "you'll see the
 * feature and can use it", where `enabled` means "you've opted in". Blocking globally also
 * writes `blocked` to every feature, so the master and per-feature views agree.
 *
 * Order matters — the cases overlap, and the global switch outranks per-feature noise.
 */
export function aiControlsPosture(config) {
    if (!config || typeof config !== 'object') {
        return undefined;
    }
    const features = Object.keys(config).filter((key) => key !== 'default');
    if (config.default === 'blocked') {
        return 'blocked_all';
    }
    const enabled = features.filter((key) => config[key] === 'enabled').length;
    const blocked = features.filter((key) => config[key] === 'blocked').length;
    if (enabled && blocked) {
        return 'mixed';
    }
    if (blocked) {
        return features.length && blocked === features.length
            ? 'blocked_all'
            : 'blocked_some';
    }
    if (enabled) {
        return 'enabled_some';
    }
    return 'neutral';
}

const MS_PER_DAY = 24 * 60 * 60 * 1000;

// Per-signal extraction from a UITour getConfiguration() payload. Firefox-specific and
// therefore quarantined here. Field names verified against UITour.sys.mjs in
// mozilla-central. Extractors are called with the config object and the current time
// (ms); only `days_since_last_session` needs the latter.
const UITOUR_EXTRACTORS = {
    is_default_browser: function (config) {
        return config.defaultBrowser;
    },
    // Reads the `fxa` key: `config.setup` here is `!!(await fxAccounts.getSignedInUser())`,
    // a genuine signed-in check. The `sync` key's `setup` field only reports that Sync has
    // been configured, and is marked deprecated in UITour.sys.mjs.
    fxa_signed_in: function (config) {
        return config.setup;
    },
    // Whole weeks, reported directly. Not converted to days: UITour only exposes weeks, so
    // multiplying would imply a precision that is not there.
    profile_age_weeks: function (config) {
        return typeof config.profileCreatedWeeksAgo === 'number'
            ? config.profileCreatedWeeksAgo
            : undefined;
    },
    // `previousSessionEnd` is a ms timestamp written only when Firefox fully quits, and
    // defaults to `0` when no previous session was ever recorded. `0` is treated as
    // unavailable rather than computed through, which would otherwise read as decades
    // lapsed for a brand-new profile.
    days_since_last_session: function (config, now) {
        const previousSessionEnd = config.previousSessionEnd;
        if (typeof previousSessionEnd !== 'number' || previousSessionEnd <= 0) {
            return undefined;
        }
        return Math.floor((now - previousSessionEnd) / MS_PER_DAY);
    },
    // Whole weeks, reported directly, mirroring profile_age_weeks. `null` means the
    // profile has never been reset.
    profile_reset_weeks_ago: function (config) {
        return typeof config.profileResetWeeksAgo === 'number'
            ? config.profileResetWeeksAgo
            : undefined;
    },
    ai_controls: aiControlsPosture
};

/**
 * UITour — Firefox-only browser state, read via a ping-gated getConfiguration under a
 * per-key budget. A ping or getConfiguration that never answers
 * leaves the read pending until the budget expires, then rejects (⇒ not-matched).
 * Injectable `uiTour`, `timeout`, and `now`.
 */
export function createUITourReader(options) {
    const opts = options || {};
    const uiTour =
        opts.uiTour || (mozillaGlobal() ? mozillaGlobal().UITour : null);
    const timeout = opts.timeout || PER_UITOUR_KEY_TIMEOUT_MS;
    const now = opts.now || Date.now;
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
                            const value = extractor(config || {}, now());
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
 * URL — a signal read from the current URL. Most URL signals are named
 * after a query param and read verbatim; two are special-cased:
 *
 *   - `oldversion` is a version signal (Firefox's just-updated flow sends it); its value
 *     is normalized the same way `firefox_version` is (bare / rv: / fully-qualified).
 *   - `locale` is the page locale, read from an explicit `?locale=` override and falling
 *     back to the `<html lang>` attribute (server-rendered on the resolver page).
 *   - `language` is that same locale with the region dropped, so one condition covers
 *     every regional variant of a language.
 *
 * Injectable `search` string, `root` element, and `lang` override.
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

    const root =
        opts.root ||
        (typeof document !== 'undefined' ? document.documentElement : null);

    function htmlLang() {
        if (opts.lang !== undefined) {
            return opts.lang;
        }
        return root && typeof root.getAttribute === 'function'
            ? root.getAttribute('lang')
            : null;
    }

    return {
        read: function (descriptor) {
            return new Promise(function (resolve, reject) {
                if (descriptor.name === 'oldversion') {
                    if (params.has('oldversion')) {
                        resolve(normalizeVersion(params.get('oldversion')));
                    } else {
                        reject();
                    }
                    return;
                }
                if (
                    descriptor.name === 'locale' ||
                    descriptor.name === 'language'
                ) {
                    // Explicit ?locale= wins; otherwise fall back to <html lang>.
                    const locale = params.has('locale')
                        ? params.get('locale')
                        : htmlLang();
                    if (locale) {
                        // `language` is the same value with the region dropped, so one
                        // condition matches every regional variant.
                        resolve(
                            descriptor.name === 'language'
                                ? baseLanguage(locale)
                                : locale
                        );
                    } else {
                        reject();
                    }
                    return;
                }
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
 * Compose the four adapters into the provider the evaluator consumes.
 *
 * @param manifest signal name -> { source, browserStateKey?, valueType? }
 * @param options  injected dependencies passed through to each adapter (root, client,
 *                 uiTour, search, timeout).
 */
export function createProvider(manifest, options) {
    const opts = options || {};
    const signalManifest = manifest || {};
    // Fake signal values (preview_signal) resolve immediately; everything else
    // reads live through the source adapters.
    const fakes = opts.fakes || {};
    const readers = {};
    readers[SOURCE_CDN_GEO] = createGeoReader(opts);
    readers[SOURCE_USER_AGENT] = createUserAgentReader(opts);
    readers[SOURCE_UITOUR] = createUITourReader(opts);
    readers[SOURCE_URL] = createUrlReader(opts);

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
            if (Object.prototype.hasOwnProperty.call(fakes, name)) {
                return Promise.resolve(fakes[name]);
            }
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
