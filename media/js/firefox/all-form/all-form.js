/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import { batch, computed, effect, signal } from '@preact/signals-core';

// State in this module is organized in four layers, and each layer only
// depends on the one above it:
//
//   1. Sources     — the four writable signals on the element. The only things
//                    anything assigns to.
//   2. Provenance  — a small state machine over *how* the current selection
//                    came to be, which is the one piece of state that is not a
//                    function of the choices themselves.
//   3. Derived     — computeds. Every one of them returns a primitive, because
//                    signals-core only skips notifying subscribers when the
//                    recomputed value is `===` the previous one. Returning a
//                    fresh object or a `URL` instance would mark the computed
//                    dirty on every keystroke and rewrite the DOM for nothing.
//   4. Effects     — the only things that touch the DOM. Each reads the
//                    narrowest computed it can so unrelated changes don't wake
//                    it up.
//
// The DOM is a write target, never a source of truth: nothing reads state back
// out of it, and nothing scans it per input event.

// ---------------------------------------------------------------------------
// Data
//
// Everything this module used to hardcode — the availability matrix, every URL,
// and every string of copy — is serialized into the page by
// springfield/firefox/all_form.py, which is the single source of truth for all
// of it. Nothing user-visible is written in this file.
//
// The one URL still built here is the bouncer one, because it is the only one
// that depends on the chosen language, and the language changes without a page
// load. It gets the pieces (`bouncerUrl`, `bouncerChannels`) instead.
// ---------------------------------------------------------------------------

const DATA = readData();

function readData() {
    const island = document.getElementById('allFormData');
    if (!island) throw new Error('Missing #allFormData data island');
    return JSON.parse(island.textContent);
}

const OS_VALUES = new Set(DATA.osValues);
const RELEASE_VALUES = new Set(Object.keys(DATA.unsupportedPlatformsByRelease));

const MOBILE_OS = new Set(DATA.mobileOS);
// The Windows options with a Microsoft Store listing. The MSI builds are for
// corporate IT to deploy and have no store equivalent.
const MICROSOFT_STORE_OS = new Set(DATA.microsoftStoreOS);
// ESR 115 has no builds for these locales (mozilla/bedrock#15437).
const ESR_115_UNAVAILABLE_LOCALES = new Set(DATA.esr115UnavailableLocales);

const MESSAGES = DATA.messages;

// The only release values this file names directly: the option list is
// specifically about them. Every other release is just a key it passes through.
const RELEASES = {
    STABLE: 'stable',
    ESR: 'esr',
    ESR_NEXT: 'esr-next',
    ESR_115: 'esr-115'
};

// Coarse platform grouping. Most copy and most conditional options care about
// the family rather than the exact build, and the family changes far less often
// than the OS does — `win64` to `win64-msi` leaves it alone — so computeds keyed
// on it stay quiet through more of the form's state space.
const PLATFORM = {
    IOS: 'ios',
    ANDROID: 'android',
    WINDOWS: 'windows',
    MACOS: 'macos',
    LINUX: 'linux'
};

// Coarser again, and only for the two link tables: there is one set of desktop
// release-notes and system-requirements pages, not one per desktop OS. Mirrors
// all_form.get_link_family().
function linkFamily(os) {
    return MOBILE_OS.has(os) ? os : 'desktop';
}

function isMobileOS(os) {
    return MOBILE_OS.has(os);
}

function platformFamily(os) {
    if (!os) return '';
    if (isMobileOS(os)) return os;
    if (os.startsWith('win')) return PLATFORM.WINDOWS;
    if (os.startsWith('osx')) return PLATFORM.MACOS;
    return PLATFORM.LINUX;
}

function isMobileFamily(family) {
    return family === PLATFORM.IOS || family === PLATFORM.ANDROID;
}

/**
 * Whether a release has a build for a platform.
 *
 * An empty platform means nothing has been chosen yet, which is not a conflict —
 * the form is simply incomplete, and `VIEW.EMPTY` covers that case.
 */
function releaseSupportsPlatform(release, platform) {
    if (!platform) return true;
    if (!RELEASE_VALUES.has(release))
        throw new RangeError(`Unknown release: ${release}`);
    if (!OS_VALUES.has(platform))
        throw new RangeError(`Unknown platform: ${platform}`);

    return !DATA.unsupportedPlatformsByRelease[release].includes(platform);
}

// ---------------------------------------------------------------------------
// URL builders
//
// These return strings rather than `URL` objects on purpose: a fresh `URL` is
// never `===` the last one, so holding them in signals would rewrite `link.href`
// on every input event.
// ---------------------------------------------------------------------------

function bouncerOS(os) {
    return os.endsWith('-msi') || os.endsWith('-pkg') ? os.slice(0, -4) : os;
}

function bouncerProduct(os, release, language) {
    const name = ['firefox', DATA.bouncerChannels[release]];
    if (os.endsWith('-pkg')) name.push('pkg');
    if (os.endsWith('-msi')) name.push('msi');
    name.push('latest');
    // Nightly uses a different product name for localized builds.
    if (release === 'nightly' && language !== 'en-US') name.push('l10n');
    name.push('ssl');
    return name.filter(Boolean).join('-');
}

function bouncerLang(os, language) {
    // The macOS build for Japanese has its own locale code.
    return os.startsWith('osx') && language === 'ja' ? 'ja-JP-mac' : language;
}

/**
 * A download.mozilla.org URL, or '' for mobile (installed from a store) and for
 * an unchosen platform.
 *
 * The only URL built rather than looked up, because it is the only one the
 * chosen language reaches.
 */
function downloadURL(os, release, language) {
    if (!os || isMobileOS(os)) return '';

    const url = new URL(DATA.bouncerUrl);
    url.searchParams.set('os', bouncerOS(os));
    url.searchParams.set('product', bouncerProduct(os, release, language));
    url.searchParams.set('lang', bouncerLang(os, language));
    return url.href;
}

/**
 * Look a URL out of one of the {family: {release: url}} tables.
 *
 * A missing entry is a release the platform has no page for, which only happens
 * for pairs the conflict view covers, so '' is the right answer rather than a
 * throw — the link is not on screen to be clicked.
 */
function familyURL(table, os, release) {
    return table[linkFamily(os)]?.[release] ?? '';
}

function releaseNotesURL(os, release) {
    return familyURL(DATA.supportLinks.releaseNotes.urls, os, release);
}

function systemRequirementsURL(os, release) {
    return familyURL(DATA.supportLinks.systemRequirements.urls, os, release);
}

/**
 * What the main download button is for a given selection.
 *
 * One pure function describing the whole button, rather than three imperative
 * writes into three signals. The element wraps each field in its own computed so
 * an OS change that leaves the label alone only rewrites the href.
 *
 * The label and icon are looked up by platform family — they never depend on the
 * exact build. The href does: a store URL for mobile, the bouncer URL otherwise.
 */
function resolvePrimaryAction(os, release, href) {
    const family = isMobileOS(os) ? os : 'desktop';
    const action = DATA.options.primary[family]?.[release];
    if (!action) return { label: '', icon: 'downloads', href: '' };

    return {
        label: action.label,
        icon: action.icon,
        href: isMobileOS(os) ? (DATA.storeUrls[os][release] ?? '') : href
    };
}

// ---------------------------------------------------------------------------
// Provenance
//
// How the current selection came to be. This is the one piece of high-level
// state that genuinely needs a machine: you cannot tell from {os, release}
// alone whether the visitor chose them, a link prefilled them, or UA detection
// guessed them — and that is exactly what decides whether an incompatible
// selection gets announced or absorbed silently. Guessing wrong and then
// scolding someone for a guess we made is the failure mode to avoid.
//
// Compatibility deliberately is *not* modelled here. It is a pure function of
// the choices, so making it a state would mean sending an event on every change
// and keeping a second copy of the truth that can drift. It is a computed.
// ---------------------------------------------------------------------------

const PROVENANCE = {
    PRISTINE: 'pristine', // server defaults, nothing chosen
    DETECTED: 'detected', // UA detection filled it in — never scold
    PREFILLED: 'prefilled', // query params — announce conflicts
    EDITED: 'edited' // the visitor touched a control — announce conflicts
};

const EVENT = {
    PREFILL: 'PREFILL',
    DETECT: 'DETECT',
    EDIT: 'EDIT'
};

const TRANSITIONS = {
    [PROVENANCE.PRISTINE]: {
        [EVENT.PREFILL]: PROVENANCE.PREFILLED,
        [EVENT.DETECT]: PROVENANCE.DETECTED,
        [EVENT.EDIT]: PROVENANCE.EDITED
    },
    [PROVENANCE.PREFILLED]: { [EVENT.EDIT]: PROVENANCE.EDITED },
    [PROVENANCE.DETECTED]: { [EVENT.EDIT]: PROVENANCE.EDITED },
    [PROVENANCE.EDITED]: {}
};

// ---------------------------------------------------------------------------
// Results pane
// ---------------------------------------------------------------------------

const VIEW = {
    EMPTY: 'empty', // nothing chosen yet — prompt, don't scold
    OPTIONS: 'options', // compatible — here are the downloads
    CONFLICT: 'conflict' // incompatible — explain why there are none
};

// Mirrors the OPTION_* constants in all_form.py. These keys are the contract
// with the server-rendered markup: each option element carries its key in
// `data-download-option`, and that is how this file finds the one to adopt.
const DOWNLOAD_OPTION = {
    FALLBACK: 'fallback',
    APT: 'apt',
    ESR_NEXT: 'esr-next',
    PRIMARY: 'primary',
    ESR_115: 'esr-115',
    APK: 'apk',
    MICROSOFT_STORE: 'microsoft-store'
};

// `or` dividers go between adjacent options that are alternatives to each other.
// Asides sit alongside the whole set and never get one.
const GROUP = { DOWNLOAD: 'download', ASIDE: 'aside' };

const DOWNLOAD_OPTION_GROUPS = {
    [DOWNLOAD_OPTION.FALLBACK]: GROUP.ASIDE,
    [DOWNLOAD_OPTION.APT]: GROUP.ASIDE,
    [DOWNLOAD_OPTION.ESR_NEXT]: GROUP.DOWNLOAD,
    [DOWNLOAD_OPTION.PRIMARY]: GROUP.DOWNLOAD,
    [DOWNLOAD_OPTION.ESR_115]: GROUP.DOWNLOAD,
    [DOWNLOAD_OPTION.APK]: GROUP.DOWNLOAD,
    [DOWNLOAD_OPTION.MICROSOFT_STORE]: GROUP.DOWNLOAD
};

const SUPPORT_LINK = {
    RELEASE_NOTES: 'release-notes',
    SYSTEM_REQUIREMENTS: 'system-requirements',
    PRIVACY: 'privacy'
};

// ---------------------------------------------------------------------------
// Temporary: state debugging and timing
//
// TODO: remove this section, its call sites, and the `label`/`name` arguments
// that only exist to feed it, before this ships.
//
// Two independent flags, each settable as a query param (`?debug`, `?measure`,
// or both) or as localStorage (`allFormDebug`, `allFormMeasure`) to survive
// reloads. Both are preserved across the history rewrite.
//
// `?debug` — a collapsed log line per state change, expanding to the full
// snapshot and a count of how many times each effect has run. The counts are
// the quick way to check the graph is as narrow as it looks: changing only the
// language should leave `render:options` and `sync:release-options` untouched.
//
// `?measure` — User Timing marks and measures around every DOM write, under the
// `all-form:` prefix so they filter cleanly in the Performance panel:
//
//     all-form:init             the whole first-paint setup
//     all-form:update           one input event, start to finish
//     all-form:effect:<label>   a single effect run
//
// Keep them separate when you care about the numbers: `?debug` logging costs
// more than the work it is reporting on, so measure with `?measure` alone.
//
// Either flag exposes `$0.debug` on the element: `.state()`, `.effects()`,
// `.log()`, `.timings()`, `.clearTimings()`.
// ---------------------------------------------------------------------------

const DEBUG = hasDebugFlag('debug', 'allFormDebug');
const MEASURE = hasDebugFlag('measure', 'allFormMeasure');

const MEASURE_PREFIX = 'all-form:';

function hasDebugFlag(param, storageKey) {
    if (new URLSearchParams(window.location.search).has(param)) return true;
    try {
        return Boolean(window.localStorage.getItem(storageKey));
    } catch {
        // Storage can be unavailable (private mode, blocked cookies).
        return false;
    }
}

/**
 * Run `fn`, leaving a mark at its start and a measure spanning it.
 *
 * The start mark is cleared once measured so the entry buffer holds only the
 * measures — the timeline recording keeps both either way.
 */
function measure(name, fn) {
    if (!MEASURE) return fn();

    const startMark = `${name}:start`;
    performance.mark(startMark);
    try {
        return fn();
    } finally {
        performance.measure(name, startMark);
        performance.clearMarks(startMark);
    }
}

/** count / total / mean / max per measure, in ms. */
function timings() {
    const stats = new Map();

    for (const entry of performance.getEntriesByType('measure')) {
        if (!entry.name.startsWith(MEASURE_PREFIX)) continue;
        const name = entry.name.slice(MEASURE_PREFIX.length);
        const stat = stats.get(name) ?? { count: 0, total: 0, max: 0 };
        stat.count += 1;
        stat.total += entry.duration;
        stat.max = Math.max(stat.max, entry.duration);
        stats.set(name, stat);
    }

    const round = (value) => Math.round(value * 1000) / 1000;

    return Object.fromEntries(
        Array.from(stats, ([name, { count, total, max }]) => [
            name,
            {
                count,
                total: round(total),
                mean: round(total / count),
                max: round(max)
            }
        ]).sort(([, a], [, b]) => b.total - a.total)
    );
}

function clearTimings() {
    for (const entry of performance.getEntriesByType('measure')) {
        if (entry.name.startsWith(MEASURE_PREFIX))
            performance.clearMeasures(entry.name);
    }
}

/* eslint-disable no-console */
const DEBUG_STYLE = 'color: #ff6611; font-weight: bold';

function debugLog(message) {
    console.log(`%c[all-form]%c ${message}`, DEBUG_STYLE, 'color: inherit');
}

function debugSnapshot(summary, snapshot, effectRuns) {
    console.groupCollapsed(
        `%c[all-form]%c ${summary}`,
        DEBUG_STYLE,
        'color: inherit'
    );
    console.table(snapshot);
    console.table(effectRuns);
    console.groupEnd();
}
/* eslint-enable no-console */

// ---------------------------------------------------------------------------
// Element
// ---------------------------------------------------------------------------

class FirefoxDownloadFormElement extends HTMLElement {
    // ── Layer 1: sources ───────────────────────────────────────────────────

    #os = signal('');
    #release = signal(RELEASES.STABLE);
    #language = signal('en-US');
    #provenance = signal(PROVENANCE.PRISTINE);

    get os() {
        return this.#os.value;
    }
    get release() {
        return this.#release.value;
    }
    get language() {
        return this.#language.value;
    }
    get provenance() {
        return this.#provenance.value;
    }

    // ── Layer 2: the provenance machine ────────────────────────────────────

    /**
     * Advance the provenance machine. Events with no transition out of the
     * current state are ignored, so the repeated EDIT events every keystroke
     * produces are a no-op write after the first one and wake nothing up.
     */
    #send(event) {
        const next = TRANSITIONS[this.#provenance.value][event];
        if (next) this.#provenance.value = next;
    }

    // ── Layer 3: derived state ─────────────────────────────────────────────

    #platformFamily = computed(() => platformFamily(this.#os.value));

    #isMobile = computed(() => isMobileFamily(this.#platformFamily.value));

    #isCompatible = computed(() =>
        releaseSupportsPlatform(this.#release.value, this.#os.value)
    );

    #view = computed(() => {
        if (!this.#os.value) return VIEW.EMPTY;
        return this.#isCompatible.value ? VIEW.OPTIONS : VIEW.CONFLICT;
    });

    #downloadHref = computed(() =>
        downloadURL(this.#os.value, this.#release.value, this.#language.value)
    );

    // Neither of these reads the language, so changing it leaves them alone.
    #releaseNotesHref = computed(() =>
        releaseNotesURL(this.#os.value, this.#release.value)
    );
    #systemRequirementsHref = computed(() =>
        systemRequirementsURL(this.#os.value, this.#release.value)
    );

    #primary = computed(() =>
        resolvePrimaryAction(
            this.#os.value,
            this.#release.value,
            this.#downloadHref.value
        )
    );

    #isESR = computed(() => this.#release.value === RELEASES.ESR);

    #hasApt = computed(() => this.#platformFamily.value === PLATFORM.LINUX);

    // Gated on the server saying a second ESR exists, the same as
    // get_esr_next_download_url() is. Between ESR cycles there is no next
    // version and no option, on either side.
    #hasESRNext = computed(
        () =>
            this.#isESR.value &&
            DATA.options.esrNext.available &&
            releaseSupportsPlatform(RELEASES.ESR_NEXT, this.#os.value)
    );

    // The only download option gated on language: ESR 115 predates a couple of
    // locales and has no build for them, so offering it would link to a 404.
    #hasESR115 = computed(
        () =>
            this.#isESR.value &&
            releaseSupportsPlatform(RELEASES.ESR_115, this.#os.value) &&
            !ESR_115_UNAVAILABLE_LOCALES.has(this.#language.value)
    );

    // Keyed on the exact OS rather than the family: the MSI builds are Windows
    // but have no Store listing, and that distinction is the whole point here.
    // Which releases have a listing is not a second list to keep in step —
    // `hrefs` already says, by having an entry or a null.
    #hasMicrosoftStore = computed(
        () =>
            MICROSOFT_STORE_OS.has(this.#os.value) &&
            Boolean(DATA.options.microsoftStore.hrefs[this.#release.value])
    );

    // Nightly APK URLs contain a build timestamp product details does not carry,
    // so the server serializes `null` for them and there is no option to show.
    #hasApk = computed(
        () =>
            this.#os.value === PLATFORM.ANDROID &&
            Boolean(DATA.options.apk.hrefs[this.#release.value])
    );

    /**
     * Which download options are visible, in render order, as a single string.
     *
     * Being a string is the point: it only changes when the *set* of options
     * changes, so choosing a different language — or any change that leaves the
     * same options on screen — never re-runs the reconciler. What each option
     * says is separate, and lives in the options' own content computeds.
     */
    #structure = computed(() => {
        switch (this.#view.value) {
            case VIEW.EMPTY:
                return DOWNLOAD_OPTION.FALLBACK;
            case VIEW.CONFLICT:
                return '';
            default:
                // Same order as all_form.get_download_option_list(), so the
                // server-rendered list and this one agree.
                return [
                    this.#hasApt.value && DOWNLOAD_OPTION.APT,
                    this.#hasESRNext.value && DOWNLOAD_OPTION.ESR_NEXT,
                    DOWNLOAD_OPTION.PRIMARY,
                    this.#hasESR115.value && DOWNLOAD_OPTION.ESR_115,
                    this.#hasApk.value && DOWNLOAD_OPTION.APK,
                    this.#hasMicrosoftStore.value &&
                        DOWNLOAD_OPTION.MICROSOFT_STORE
                ]
                    .filter(Boolean)
                    .join(' ');
        }
    });

    // ── Element references, captured once ──────────────────────────────────

    #form;
    #resultsPane;
    #downloadOptionsPane;
    #incompatiblePane;
    #supportLinksPane;
    #languageMessage;

    /** Download option key -> its element. Built once; reconciled, never rebuilt. */
    #downloadOptions = new Map();
    /** `or` dividers, cached by the option key they precede. */
    #dividers = new Map();
    /**
     * Release value -> { option, placeholder }, so swapping an unavailable
     * release out of the select is a map lookup rather than a childNodes scan
     * on every input event.
     */
    #releaseOptions = new Map();

    /** The selects, in DOM order. */
    #fields = [];
    /**
     * Control -> the error message currently rendered for it, so showing an
     * error is idempotent and clearing one knows what to undo.
     */
    #fieldErrors = new Map();

    #disposers = [];

    /** Effect label -> how many times it has run. Debug only. */
    #effectRuns = new Map();

    /**
     * Everything worth looking at, in one object. Debug only: it returns a fresh
     * object so it is dirty on every change, which is fine because nothing
     * subscribes to it unless DEBUG is on — and computeds are lazy, so with
     * DEBUG off it is never evaluated at all.
     */
    #snapshot = computed(() => ({
        provenance: this.#provenance.value,
        view: this.#view.value,
        os: this.#os.value,
        release: this.#release.value,
        language: this.#language.value,
        platformFamily: this.#platformFamily.value,
        isMobile: this.#isMobile.value,
        isCompatible: this.#isCompatible.value,
        structure: this.#structure.value,
        downloadHref: this.#downloadHref.value,
        releaseNotesHref: this.#releaseNotesHref.value,
        systemRequirementsHref: this.#systemRequirementsHref.value
    }));

    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
        this.shadowRoot.innerHTML = '<slot></slot>';
        this.shadowRoot.addEventListener('slotchange', this);
    }

    disconnectedCallback() {
        for (const dispose of this.#disposers) dispose();
        this.#disposers.length = 0;
    }

    /**
     * Register an effect and keep its disposer so teardown is possible.
     *
     * With both debug flags off, `run` is `fn` untouched — no wrapper, no cost.
     */
    #effect(fn, label = 'anonymous') {
        let run = fn;

        // The debug logger is not a DOM update and would only skew the numbers.
        if (MEASURE && !label.startsWith('debug:')) {
            const name = `${MEASURE_PREFIX}effect:${label}`;
            const measured = run;
            run = () => measure(name, measured);
        }

        if (DEBUG) {
            this.#effectRuns.set(label, 0);
            const counted = run;
            run = () => {
                this.#effectRuns.set(label, this.#effectRuns.get(label) + 1);
                counted();
            };
        }

        this.#disposers.push(effect(run));
    }

    handleEvent(event) {
        switch (event.type) {
            case 'slotchange':
                this.#handleSlotChange(event);
                break;
            case 'input':
                this.#handleInput(event);
                break;
            case 'invalid':
                this.#handleInvalid(event);
                break;
            case 'submit':
                event.preventDefault();
                // TODO: maybe since a submit is expected we just follow the
                // most prominent link? Or we direct users to the options?
                break;
        }
    }

    // ── Setup ──────────────────────────────────────────────────────────────

    #handleSlotChange() {
        const form = this.querySelector(':scope > form:first-child');
        if (!form) return;

        this.#form = form;

        measure(`${MEASURE_PREFIX}init`, () => {
            // Seed the machine before anything can rewrite the query string.
            this.#seedProvenance();

            batch(() => {
                this.#os.value = this.#form.elements.os.value;
                this.#release.value = this.#form.elements.release.value;
                this.#language.value = this.#form.elements.language.value;
            });

            this.#collectElements();
            this.#collectReleaseOptions();
            this.#createDownloadOptions();
            this.#createSupportLinks();
            this.#registerEffects();
        });

        this.#form.addEventListener('submit', this);
        this.#form.addEventListener('input', this);
        this.#form.addEventListener('invalid', this, true);

        this.shadowRoot.removeEventListener('slotchange', this);
    }

    /**
     * Work out how the form got its current values.
     *
     * Query params win over detection, and the inline detection script in
     * base.html gates itself the same way, so the two agree on which fields the
     * visitor actually asked for.
     */
    #seedProvenance() {
        const params = new URLSearchParams(window.location.search);
        if (
            params.has('os') ||
            params.has('release') ||
            params.has('language')
        ) {
            this.#send(EVENT.PREFILL);
        } else if (this.#form.dataset.autoDetectedOs) {
            this.#send(EVENT.DETECT);
        }
    }

    #collectElements() {
        const { os, release, language } = this.#form.elements;
        this.#fields = [os, release, language];

        this.#resultsPane = this.querySelector('.c-results');
        this.#downloadOptionsPane = this.#resultsPane.querySelector(
            '.c-download-options'
        );
        this.#incompatiblePane = this.#resultsPane.querySelector(
            '.c-incompatible-choices'
        );

        // Server-rendered, and already showing if the page loaded on a store app.
        this.#languageMessage = language
            .closest('.fl-field-wrap')
            .querySelector('.c-language-message');
    }

    /**
     * Index the release select's options in a single pass.
     *
     * Setting `hidden` on an option element has a number of issues:
     *
     * - Safari doesn’t respect it (unless using customizable select).
     * - Screen readers still seem to count them when presenting the item number
     *   of the current option.
     * - In NVDA + Firefox, the arrow key select navigation (form mode) becomes
     *   completely broken.
     *
     * So instead an unavailable option is swapped out for a comment node that
     * holds its place, and swapped back in when it becomes available again.
     * Holding both nodes here means the swap is a map lookup and a
     * `replaceWith`, instead of re-deriving the pairing from the DOM every time
     * the platform changes.
     */
    #collectReleaseOptions() {
        for (const option of this.#form.elements.release.options) {
            this.#releaseOptions.set(option.value, {
                option,
                placeholder: new Comment(
                    `${option.value}:${option.textContent}`
                )
            });
        }
    }

    /**
     * Build every option element once. They are reconciled from here on, never
     * rebuilt, and stay detached until #structure asks for them.
     *
     * Every label, icon, and class comes from DATA.options — the same table
     * all_form.get_download_option_list() renders the result page from, so the
     * list this builds and the list that page shows are the same list.
     */
    #createDownloadOptions() {
        const { apt, esrNext, esr115, apk, microsoftStore } = DATA.options;

        // The server-rendered submit button, which is the whole results pane
        // until we get here: it is the right prompt before anything is chosen and
        // the only working affordance without JS. Kept and treated as one more
        // entry in the list rather than destroyed on upgrade.
        this.#downloadOptions.set(
            DOWNLOAD_OPTION.FALLBACK,
            this.#downloadOptionsPane.querySelector(
                `[data-download-option="${DOWNLOAD_OPTION.FALLBACK}"]`
            )
        );

        this.#downloadOptions.set(
            DOWNLOAD_OPTION.APT,
            this.#createDownloadButton({
                name: DOWNLOAD_OPTION.APT,
                label: apt.label,
                href: apt.href,
                icon: apt.icon,
                additionalClasses: apt.classes
            })
        );

        this.#downloadOptions.set(
            DOWNLOAD_OPTION.ESR_NEXT,
            this.#createDownloadButton({
                name: DOWNLOAD_OPTION.ESR_NEXT,
                label: esrNext.label,
                icon: esrNext.icon,
                additionalClasses: esrNext.classes,
                href: () =>
                    downloadURL(
                        this.#os.value,
                        RELEASES.ESR_NEXT,
                        this.#language.value
                    )
            })
        );

        this.#downloadOptions.set(
            DOWNLOAD_OPTION.PRIMARY,
            this.#createDownloadButton({
                name: DOWNLOAD_OPTION.PRIMARY,
                additionalClasses: ['button-primary'],
                // Each field gets its own computed, so a change that only moves
                // the href leaves the label's text node untouched.
                label: () => this.#primary.value.label,
                icon: () => this.#primary.value.icon,
                href: () => this.#primary.value.href
            })
        );

        this.#downloadOptions.set(
            DOWNLOAD_OPTION.ESR_115,
            this.#createDownloadButton({
                name: DOWNLOAD_OPTION.ESR_115,
                label: esr115.label,
                icon: esr115.icon,
                additionalClasses: esr115.classes,
                href: () =>
                    downloadURL(
                        this.#os.value,
                        RELEASES.ESR_115,
                        this.#language.value
                    ),
                recommendation: () =>
                    esr115.recommendations[this.#platformFamily.value] ?? ''
            })
        );

        this.#downloadOptions.set(
            DOWNLOAD_OPTION.APK,
            this.#createDownloadButton({
                name: DOWNLOAD_OPTION.APK,
                label: apk.label,
                icon: apk.icon,
                additionalClasses: apk.classes,
                href: () => apk.hrefs[this.#release.value] ?? ''
            })
        );

        this.#downloadOptions.set(
            DOWNLOAD_OPTION.MICROSOFT_STORE,
            this.#createDownloadButton({
                name: DOWNLOAD_OPTION.MICROSOFT_STORE,
                label: microsoftStore.label,
                icon: microsoftStore.icon,
                additionalClasses: microsoftStore.classes,
                href: () => microsoftStore.hrefs[this.#release.value] ?? ''
            })
        );
    }

    /**
     * The support links row. Built here rather than server-rendered for the same
     * reason as the options: it describes one selection, and the form page is
     * where the selection changes.
     */
    #createSupportLinks() {
        const { releaseNotes, systemRequirements, privacy } = DATA.supportLinks;

        this.#supportLinksPane = document.createElement('div');
        this.#supportLinksPane.classList.add('c-support-links');
        this.#supportLinksPane.append(
            this.#createSupportLink({
                key: SUPPORT_LINK.RELEASE_NOTES,
                label: releaseNotes.label,
                href: () => this.#releaseNotesHref.value
            }),
            this.#createSupportLink({
                key: SUPPORT_LINK.SYSTEM_REQUIREMENTS,
                label: systemRequirements.label,
                href: () => this.#systemRequirementsHref.value
            }),
            this.#createSupportLink({
                key: SUPPORT_LINK.PRIVACY,
                label: privacy.label,
                href: privacy.url
            })
        );
        this.#resultsPane.append(this.#supportLinksPane);
    }

    // ── Layer 4: effects ───────────────────────────────────────────────────

    #registerEffects() {
        // Reflect the state machine onto the host, so it is inspectable in
        // devtools and available to CSS. Nothing visual depends on these — the
        // logo follows the release select itself.
        this.#effect(() => {
            this.dataset.view = this.#view.value;
        }, 'attr:view');
        this.#effect(() => {
            this.dataset.provenance = this.#provenance.value;
        }, 'attr:provenance');
        this.#effect(() => {
            this.dataset.os = this.#os.value;
        }, 'attr:os');
        this.#effect(() => {
            this.dataset.release = this.#release.value;
        }, 'attr:release');
        this.#effect(() => {
            this.dataset.language = this.#language.value;
        }, 'attr:language');

        // Keep the query string in step with what the visitor chose. Gated on
        // an actual edit: a detected platform is a guess, and writing it to the
        // URL would make the next reload look like a deliberate prefill.
        this.#effect(() => {
            if (this.#provenance.value !== PROVENANCE.EDITED) return;
            const params = {
                os: this.#os.value,
                release: this.#release.value,
                language: this.#language.value
            };
            if (DEBUG) params.debug = '';
            if (MEASURE) params.measure = '';
            const url = new URL(window.location);
            url.search = new URLSearchParams(params);
            history.replaceState(null, '', url);
        }, 'sync:url');

        // Which releases the platform can actually offer.
        this.#effect(() => {
            const os = this.#os.value;
            const selected = this.#release.value;

            for (const [release, { option, placeholder }] of this
                .#releaseOptions) {
                const supported = releaseSupportsPlatform(release, os);

                // An unavailable option that is currently selected stays in the
                // select, disabled: changing the visitor's choice out from
                // under them hides which half of the pair is the problem.
                if (supported || release === selected) {
                    if (!option.isConnected) placeholder.replaceWith(option);
                    option.disabled = !supported;
                } else if (option.isConnected) {
                    option.replaceWith(placeholder);
                }
            }
        }, 'sync:release-options');

        // Mobile builds are multi-locale, so the language choice does not apply.
        this.#effect(() => {
            this.#form.elements.language.disabled = this.#isMobile.value;
            this.#languageMessage.hidden = !this.#isMobile.value;
        }, 'sync:language-field');

        // Compatibility is expressed as a native constraint, so the browser
        // stays the single source of validity and everything downstream —
        // `:user-invalid`, `validationMessage`, submit blocking — comes along
        // for free. Reporting it is a separate, event-driven step: see
        // #report and #handleInvalid.
        this.#effect(() => {
            this.#form.elements.release.setCustomValidity(
                this.#isCompatible.value ? '' : MESSAGES.releaseUnavailable
            );
        }, 'sync:validity');

        // The server-rendered error describes the selection the page loaded
        // with. Once the visitor edits, it is stale.
        this.#effect(() => {
            if (this.#provenance.value !== PROVENANCE.EDITED) return;
            const serverError = this.querySelector('#server-release-error');
            if (!serverError) return;
            serverError.remove();
            this.#form.elements.release.setAttribute(
                'aria-describedby',
                'release-no-js-hint'
            );
        }, 'clear:server-error');

        this.#effect(() => {
            const view = this.#view.value;
            this.#downloadOptionsPane.hidden = view === VIEW.CONFLICT;
            this.#supportLinksPane.hidden = view !== VIEW.OPTIONS;
            this.#incompatiblePane.hidden = view !== VIEW.CONFLICT;
        }, 'render:panes');

        // Structure only. Content updates happen in each option's own effects
        // and never reach this far.
        this.#effect(() => {
            this.#renderDownloadOptions(
                this.#structure.value ? this.#structure.value.split(' ') : []
            );
        }, 'render:options');

        this.#registerDebug();
    }

    /**
     * Temporary. Registered last so the run counts it prints already include
     * everything else that ran in the same flush.
     */
    #registerDebug() {
        if (!DEBUG && !MEASURE) return;

        this.debug = {
            state: () => this.#snapshot.value,
            effects: () => Object.fromEntries(this.#effectRuns),
            log: () => this.#logState('manual'),
            timings,
            clearTimings
        };

        debugLog(
            `${[DEBUG && 'debug', MEASURE && 'measure'].filter(Boolean).join(' + ')} on — ` +
                'select the <firefox-download-form> element and use ' +
                '$0.debug.state(), .effects(), .log(), .timings(), .clearTimings()'
        );

        if (!DEBUG) return;

        // #logState reads the snapshot, which is what subscribes this effect.
        this.#effect(() => this.#logState('change'), 'debug:log');
    }

    #logState(reason) {
        const snapshot = this.#snapshot.value;
        debugSnapshot(
            [
                reason,
                snapshot.provenance,
                snapshot.view,
                `${snapshot.os || '(none)'} / ${snapshot.release} / ${snapshot.language}`,
                snapshot.structure ? `[${snapshot.structure}]` : '[]'
            ].join(' · '),
            snapshot,
            Object.fromEntries(this.#effectRuns)
        );
    }

    /**
     * Lay out the visible download options in the order #structure declares.
     *
     * Order lives in one place instead of emerging from several effects
     * inserting themselves relative to each other, and dividers fall out of
     * adjacency rather than being tracked as siblings.
     */
    #renderDownloadOptions(keys) {
        const children = [];
        let previousGroup = null;

        for (const key of keys) {
            const group = DOWNLOAD_OPTION_GROUPS[key];
            if (previousGroup === GROUP.DOWNLOAD && group === GROUP.DOWNLOAD) {
                children.push(this.#divider(key));
            }
            children.push(this.#downloadOptions.get(key));
            previousGroup = group;
        }

        this.#downloadOptionsPane.replaceChildren(...children);
    }

    #divider(key) {
        if (!this.#dividers.has(key)) {
            const divider = document.createElement('div');
            divider.classList.add('c-or-divider');
            divider.textContent = MESSAGES.divider;
            this.#dividers.set(key, divider);
        }
        return this.#dividers.get(key);
    }

    // ── Event handlers ─────────────────────────────────────────────────────

    #handleInput(event) {
        if (!(event.target instanceof HTMLSelectElement)) return;

        // One measure spanning everything a single choice costs: the batched
        // signal writes, every effect they wake, and the reporting pass.
        measure(`${MEASURE_PREFIX}update`, () => {
            batch(() => {
                this.#send(EVENT.EDIT);
                this.#os.value = this.#form.elements.os.value;
                this.#release.value = this.#form.elements.release.value;
                this.#language.value = this.#form.elements.language.value;
            });

            // Custom validity has already been synced by the batch above, so
            // the browser's answer is current by the time we ask for it.
            this.#report();
        });
    }

    /**
     * Our own constraint reporting.
     *
     * The native bubble is transient — it vanishes on the next interaction and
     * a screen reader gets one shot at it — so #handleInvalid cancels it and we
     * render a message that stays put instead. `checkValidity()` is the right
     * primitive for that: it raises `invalid` for whatever fails and shows no UI
     * of its own.
     *
     * Clearing first, rather than diffing, is deliberate. It restarts the
     * deferred announcement in #setFieldError, which is the whole point of the
     * deferral: while someone is still working through the selects, a message
     * must not be announced into the middle of their next interaction.
     */
    #report() {
        for (const field of this.#fields) this.#setFieldError(field, '');

        // Only the release field reports as you edit. It carries the one
        // constraint of ours — compatibility — and it is where the explanation
        // for a conflict belongs, whichever select produced it. `required` on a
        // field left empty is not something to complain about mid-flow; native
        // submit raises that, and #handleInvalid renders it then.
        this.#form.elements.release.checkValidity();
    }

    /**
     * Render a validation failure as our own persistent message.
     *
     * Fires for our `checkValidity()` above and for the browser's own pass over
     * the form on submit, so both routes produce the same message.
     */
    #handleInvalid(event) {
        // Suppress the native bubble; we report this ourselves.
        event.preventDefault();

        // Stay quiet about a field nobody has touched yet. `:user-invalid`
        // covers the field the visitor edited directly, and after a submit
        // attempt it covers the whole form. The machine covers the case
        // `:user-invalid` cannot see: editing one field invalidating another —
        // choosing Linux 32-bit is what makes the release unavailable, and the
        // release select is where that has to be explained.
        if (
            this.#provenance.value !== PROVENANCE.EDITED &&
            !event.target.matches(':user-invalid')
        )
            return;

        this.#setFieldError(event.target, event.target.validationMessage);
    }

    /**
     * Show, update, or clear the error message for a field.
     *
     * The single way a message gets on screen and the single way it comes off,
     * whether the trigger was our own `checkValidity()` or the browser
     * validating the form on submit.
     */
    #setFieldError(control, message) {
        const current = this.#fieldErrors.get(control);
        const fieldWrap = control.closest('.fl-field-wrap');

        if (!message) {
            if (!current) return;
            clearTimeout(current.announcement);
            current.element.remove();
            fieldWrap.classList.remove('fl-field-error');
            control.ariaDescribedByElements = null;
            if (current.describedBy)
                control.setAttribute('aria-describedby', current.describedBy);
            else control.removeAttribute('aria-describedby');
            this.#fieldErrors.delete(control);
            return;
        }

        if (current) {
            if (current.message !== message) {
                current.element.textContent = message;
                current.message = message;
            }
            return;
        }

        // A server-rendered message is already saying this. Leave it be rather
        // than stacking a second copy underneath it; the clear:server-error
        // effect takes it away on the first edit and we render from then on.
        if (fieldWrap.querySelector('.fl-field-error-message')) return;

        const element = document.createElement('deferred-alert');
        element.classList.add('fl-field-error-message');
        element.textContent = message;

        // Since the validation is happening as the select element closes, the announcement-space is very busy and we risk our message being clobbered.
        // This is especially bad on iOS.
        // In order to circumvent these issues, we need to debounce the live region announcement.
        // For iOS VoiceOver, we need an extra long delay to avoid clobbering.
        // We can visually display the error immediately, but then wait for a timeout.
        // Safari tends to be quite aggressive with how it caches its accessibility tree, but if we use a shadow root to change the DOM structure, we can force it to invalidate.
        // TODO: use a more reliable/accurate way of checking for mobile.
        const announcement = setTimeout(
            () => {
                element.attachShadow({ mode: 'open' });
                element.shadowRoot.innerHTML =
                    '<div role=alert><slot></slot></div>';
            },
            matchMedia('(pointer: coarse)').matches ? 1_400 : 250
        );

        fieldWrap.classList.add('fl-field-error');
        fieldWrap.append(element);

        this.#fieldErrors.set(control, {
            element,
            message,
            announcement,
            describedBy: control.getAttribute('aria-describedby')
        });

        control.ariaDescribedByElements = [element];
    }

    // ── Widget factories ───────────────────────────────────────────────────
    //
    // Each accepts either a static string or a function. A function is wrapped
    // in a computed, which is what keeps writes minimal: the computed bails out
    // when it recomputes to the same string, so the effect that writes the DOM
    // never runs.

    #bind(source) {
        return typeof source === 'function'
            ? computed(source)
            : signal(source ?? '');
    }

    /**
     * A download option.
     *
     * The structure matches firefox/all-form/_download-options.html, which the
     * result page renders the same list from, so one set of styles covers both.
     */
    #createDownloadButton({
        name,
        label,
        href,
        icon,
        recommendation,
        additionalClasses
    } = {}) {
        const element = document.createElement('div');
        element.classList.add('c-download-option');
        element.dataset.downloadOption = name;

        const link = document.createElement('a');
        link.classList.add('fl-button');
        if (additionalClasses) link.classList.add(...additionalClasses);

        // The label lives in its own text node so writing it cannot disturb the
        // icon beside it.
        const text = document.createTextNode('');
        link.append(text);

        const labelSource = this.#bind(label);
        this.#effect(() => {
            text.data = labelSource.value;
        }, `${name}:label`);

        const hrefSource = this.#bind(href);
        this.#effect(() => {
            link.href = hrefSource.value;
        }, `${name}:href`);

        if (icon) {
            const iconElement = document.createElement('span');
            iconElement.setAttribute('aria-hidden', 'true');
            link.append(iconElement);

            const iconSource = this.#bind(icon);
            this.#effect(() => {
                iconElement.className = `fl-icon fl-icon-${iconSource.value}`;
            }, `${name}:icon`);
        }

        element.append(link);

        if (recommendation) {
            const recommendationElement = document.createElement('p');
            recommendationElement.classList.add('c-recommendation');
            element.append(recommendationElement);

            const recommendationSource = this.#bind(recommendation);
            this.#effect(() => {
                recommendationElement.textContent = recommendationSource.value;
            }, `${name}:recommendation`);
        }

        return element;
    }

    #createSupportLink({ key, label, href } = {}) {
        const element = document.createElement('a');

        const labelSource = this.#bind(label);
        this.#effect(() => {
            element.textContent = labelSource.value;
        }, `link:${key}:label`);

        const hrefSource = this.#bind(href);
        this.#effect(() => {
            element.href = hrefSource.value;
        }, `link:${key}:href`);

        return element;
    }
}

customElements.define('firefox-download-form', FirefoxDownloadFormElement);
