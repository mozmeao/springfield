/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * User Routing — dynamic condition help text in the Wagtail admin (spec §6.2).
 *
 * When an author picks a signal in a routing condition, this surfaces the valid values
 * beneath the expected-value field: the enumerated set for enum signals, or a type hint
 * plus the operator meanings for the rest. Everything human-readable comes from
 * `window.ROUTING_SIGNAL_PAYLOAD` (the registry, localized server-side in C11), so the
 * help can never drift from the evaluator and needs no English literals here.
 */

const HELP_CLASSNAME = 'routing-condition-help';
// Added to the help element (and aria-invalid on the field) when a value fails
// pre-submit validation, so the same help line doubles as the correction guidance.
const ERROR_CLASSNAME = 'routing-condition-help--invalid';
// Flag set on a wired signal <select> so re-scans never double-bind it.
const BOUND_FLAG = 'springfieldRoutingBound';
// Flag set on the edit <form> so its submit guard is attached only once.
const SUBMIT_GUARD_FLAG = 'springfieldRoutingSubmitGuard';
// Set-membership operators carry a comma-separated list (matches the Python convention).
const MEMBERSHIP_OPERATORS = ['in', 'not_in'];
// Cap on how many known values are spelled out inline (locale/country are long); the
// full set lives on the Signals reference page.
const VALUE_LIST_CAP = 15;

function siblingFieldFor(select, root, suffix) {
    // The condition's signal select and its sibling fields share an inline-panel prefix
    // and differ only by the field suffix (Wagtail InlinePanel naming).
    const name = select.getAttribute('name') || '';
    const siblingName = name.replace(/-signal$/, suffix);
    if (siblingName === name) {
        return null;
    }
    return root.querySelector('[name="' + siblingName + '"]');
}

function expectedFieldFor(select, root) {
    return siblingFieldFor(select, root, '-expected_value');
}

function operatorFieldFor(select, root) {
    return siblingFieldFor(select, root, '-operator');
}

function joinCapped(values) {
    const shown = values.slice(0, VALUE_LIST_CAP).join(', ');
    if (values.length > VALUE_LIST_CAP) {
        return shown + ', … (' + values.length + ' total)';
    }
    return shown;
}

export function buildHelpText(meta, operator) {
    if (!meta) {
        return '';
    }
    const parts = [];
    // Lead with what the signal means, so editors get context in the form.
    if (meta.description) {
        parts.push(meta.description);
    }
    // Then what to type. For a closed set (enum) or known-set string (locale/country),
    // list the accepted values — the codes, since those are what the author types. The
    // operator dropdown already shows the operators, so help never restates them.
    if (meta.enumValues && meta.enumValues.length) {
        parts.push(
            meta.hint +
                ' ' +
                meta.enumValues.map((entry) => entry.value).join(', ')
        );
    } else if (meta.values && meta.values.length) {
        parts.push(meta.hint + ' ' + joinCapped(meta.values));
    } else if (meta.hint) {
        parts.push(meta.hint);
    }
    // Only when a set-membership operator is chosen is a comma-separated list meaningful.
    if (MEMBERSHIP_OPERATORS.indexOf(operator) !== -1 && meta.commaHint) {
        parts.push(meta.commaHint);
    }
    return parts.join(' ');
}

export function filterOperators(select, payload, root) {
    // Restrict the operator dropdown to the operators legal for the chosen signal (ED-2):
    // an author should never be offered `in` on a version signal. The server-side
    // RoutingCondition.clean() stays the backstop; this is the usability half.
    const scope = root || document;
    const operatorSelect = operatorFieldFor(select, scope);
    if (!operatorSelect) {
        return null;
    }
    const meta = payload[select.value];
    // No metadata (blank/unknown signal) ⇒ leave every operator available.
    const legal =
        meta && meta.operators
            ? meta.operators.map((entry) => entry.value)
            : null;

    let selectedStillLegal = false;
    Array.prototype.forEach.call(operatorSelect.options, function (option) {
        const allowed = !legal || legal.indexOf(option.value) !== -1;
        option.hidden = !allowed;
        option.disabled = !allowed;
        if (allowed && option.value === operatorSelect.value) {
            selectedStillLegal = true;
        }
    });
    // A now-illegal selection (e.g. after switching signals) falls back to the first
    // legal operator so the field never submits an operator the signal rejects.
    if (!selectedStillLegal && legal && legal.length) {
        operatorSelect.value = legal[0];
    }
    return operatorSelect;
}

function splitList(value) {
    return String(value)
        .split(',')
        .map((entry) => entry.trim())
        .filter(Boolean);
}

export function classifyValue(meta, operator, value) {
    // Grade a condition value against RoutingCondition.clean() (ED-4), but split the verdict
    // into three so the client can block only what it should (C28):
    //   'ok'       — acceptable.
    //   'advisory' — an off-list `locale`/`country` value. `locale` is a flexible string, so a
    //                non-matching value isn't wrong: it simply fails to match at runtime and the
    //                canonical page serves (fail-safe). Shows the red hint, but never blocks.
    //   'hard'     — the server would reject it, or it would silently mis-route (a malformed
    //                boolean like "yess" → false). Blocks the save when the field is on-screen.
    if (!meta) {
        return 'ok'; // unknown/blank signal: leave it to the server
    }
    // Operator must be legal for the signal (C25 filters the dropdown; this backstops it).
    if (operator && meta.operators) {
        const legal = meta.operators.map((entry) => entry.value);
        if (legal.indexOf(operator) === -1) {
            return 'hard';
        }
    }
    const raw = String(
        value === undefined || value === null ? '' : value
    ).trim();
    if (!raw) {
        return 'hard'; // a condition always needs a value
    }
    const isMembership = MEMBERSHIP_OPERATORS.indexOf(operator) !== -1;
    // Enum: a closed set the evaluator depends on — off-list is a hard block.
    if (meta.enumValues && meta.enumValues.length) {
        const members = meta.enumValues.map((entry) => entry.value);
        const parts = isMembership ? splitList(value) : [raw];
        const allMembers =
            parts.length > 0 &&
            parts.every((part) => members.indexOf(part) !== -1);
        return allMembers ? 'ok' : 'hard';
    }
    // Known-set string (locale/country): membership is advisory, not enforced (fail-safe).
    if (meta.values && meta.values.length) {
        const parts = isMembership ? splitList(value) : [raw];
        const allMembers =
            parts.length > 0 &&
            parts.every((part) => meta.values.indexOf(part) !== -1);
        return allMembers ? 'ok' : 'advisory';
    }
    if (meta.valueType === 'boolean') {
        return /^(true|false|1|0)$/i.test(raw) ? 'ok' : 'hard';
    }
    if (meta.valueType === 'integer') {
        return /^-?\d+$/.test(raw) ? 'ok' : 'hard';
    }
    if (meta.valueType === 'version') {
        // Accept bare / rv:-prefixed / dotted forms (matches normalizeVersion).
        return /^\d+(\.\d+)*$/.test(raw.replace(/^[^\d]*/, '')) ? 'ok' : 'hard';
    }
    // Free-text string (utm_*): any non-empty value is acceptable.
    return 'ok';
}

export function validateExpectedValue(meta, operator, value) {
    // The advisory-aware "is this value acceptable?" check that drives the inline red hint:
    // anything short of 'ok' (including an off-list locale) fails here, so the author still
    // sees a correction. Whether that failure *blocks the save* is a separate question —
    // classifyValue distinguishes 'advisory' from 'hard' for that.
    return classifyValue(meta, operator, value) === 'ok';
}

function setConditionError(select, payload, scope, hasError) {
    // renderConditionHelp resets the line to the normal (valid-values) guidance; on error
    // prepend an explicit "not valid" message so it reads as an error, not just a red box.
    const help = renderConditionHelp(select, payload, scope);
    if (help) {
        if (hasError) {
            help.classList.add(ERROR_CLASSNAME);
            const meta = payload[select.value];
            if (meta && meta.invalidHint) {
                help.textContent = meta.invalidHint + ' ' + help.textContent;
            }
        } else {
            help.classList.remove(ERROR_CLASSNAME);
        }
    }
    const expected = expectedFieldFor(select, scope);
    if (expected) {
        if (hasError) {
            expected.setAttribute('aria-invalid', 'true');
        } else {
            expected.removeAttribute('aria-invalid');
        }
    }
    return expected;
}

function isFieldVisible(el) {
    // "Visible" ⇒ the field is laid out, i.e. the author is on the routing tab. `offsetParent`
    // is null (and getClientRects() empty) for a `display:none` ancestor — exactly how Wagtail
    // hides an inactive tab panel — and for a detached node. We deliberately read *rendering*,
    // not Wagtail tab state (which is brittle and fights Wagtail's own multi-tab error routing).
    if (!el) {
        return false;
    }
    return !!(el.offsetParent || el.getClientRects().length);
}

function validateConditionRow(select, payload, scope) {
    // Skip rows being deleted — they won't be saved.
    const del = siblingFieldFor(select, scope, '-DELETE');
    if (del && del.checked) {
        setConditionError(select, payload, scope, false);
        return true;
    }
    const operatorSelect = operatorFieldFor(select, scope);
    const expected = expectedFieldFor(select, scope);
    const status = classifyValue(
        payload[select.value],
        operatorSelect ? operatorSelect.value : '',
        expected ? expected.value : ''
    );
    // Always surface the red hint for anything not 'ok' — advisory and hard alike — so the
    // author sees the problem inline (on blur/change and on a blocked submit).
    setConditionError(select, payload, scope, status !== 'ok');
    // But only a *hard* failure on a *visible* field blocks the save. Advisory failures
    // (off-list locale/country — fail-safe to canonical) and rows on an inactive tab fall
    // through to the server, where Wagtail owns error/tab routing natively.
    if (status === 'hard' && isFieldVisible(expected)) {
        return false;
    }
    return true;
}

export function validateConditions(root, payload) {
    const scope = root || document;
    const selects = scope.querySelectorAll('select[name$="-signal"]');
    let firstInvalid = null;
    Array.prototype.forEach.call(selects, function (select) {
        if (!validateConditionRow(select, payload, scope) && !firstInvalid) {
            firstInvalid = expectedFieldFor(select, scope);
        }
    });
    if (firstInvalid && typeof firstInvalid.focus === 'function') {
        firstInvalid.focus();
    }
    return firstInvalid === null;
}

export function renderConditionHelp(select, payload, root) {
    const scope = root || document;
    const expected = expectedFieldFor(select, scope);
    if (!expected || !expected.parentNode) {
        return null;
    }
    // The comma hint depends on the chosen operator, so read it here.
    const operatorSelect = operatorFieldFor(select, scope);
    const operator = operatorSelect ? operatorSelect.value : '';
    let help = expected.parentNode.querySelector('.' + HELP_CLASSNAME);
    if (!help) {
        help = document.createElement('p');
        help.className = HELP_CLASSNAME;
        expected.parentNode.appendChild(help);
    }
    help.textContent = buildHelpText(payload[select.value], operator);
    return help;
}

function wireSelect(select, payload, scope) {
    // Idempotent: a select is bound once, so re-scanning after DOM changes is safe.
    if (select.dataset[BOUND_FLAG] === '1') {
        return;
    }
    select.dataset[BOUND_FLAG] = '1';
    select.addEventListener('change', function () {
        renderConditionHelp(select, payload, scope);
        filterOperators(select, payload, scope);
    });
    // Refresh the help when the operator changes too, so the comma-separated hint
    // appears/disappears with in / not in.
    const operatorSelect = operatorFieldFor(select, scope);
    if (operatorSelect) {
        operatorSelect.addEventListener('change', function () {
            renderConditionHelp(select, payload, scope);
        });
    }
    // Validate this row when the value field is committed (blur/change), so a bad value
    // turns red with its message immediately — not only when the author tries to save.
    const expected = expectedFieldFor(select, scope);
    if (expected) {
        expected.addEventListener('change', function () {
            validateConditionRow(select, payload, scope);
        });
    }
    // Initial pass filters from the pre-selected signal, so an existing rule opens with
    // its operator dropdown already scoped (and its saved operator preserved).
    renderConditionHelp(select, payload, scope);
    filterOperators(select, payload, scope);
}

function wireAll(payload, scope) {
    const selects = scope.querySelectorAll('select[name$="-signal"]');
    Array.prototype.forEach.call(selects, function (select) {
        wireSelect(select, payload, scope);
    });
}

function isRoutingForm(form) {
    return !!(
        form &&
        typeof form.querySelector === 'function' &&
        form.querySelector('select[name$="-signal"]')
    );
}

function attachSubmitGuard(payload, scope) {
    // Block a save with an illegal condition value inline, instead of round-tripping to a
    // server error (ED-4). The Wagtail page form is `novalidate` and saves via a Stimulus
    // controller whose "Saving…" spinner starts on the button *click* — so intercepting the
    // `submit` event is too late (the spinner is already up when we cancel the POST). We
    // therefore guard the submit-button **click** in the CAPTURE phase (runs before
    // Wagtail's handlers), with a `submit` backstop for keyboard/programmatic submits.
    // In the real admin `scope` is `document`; in unit tests it's the (detached) form.
    const isForm = scope.tagName === 'FORM';
    const target = isForm
        ? scope
        : typeof document !== 'undefined'
          ? document
          : null;
    const flagHost = isForm
        ? scope
        : typeof document !== 'undefined'
          ? document.documentElement
          : null;
    if (!target || !flagHost || flagHost.dataset[SUBMIT_GUARD_FLAG] === '1') {
        return;
    }
    flagHost.dataset[SUBMIT_GUARD_FLAG] = '1';

    target.addEventListener(
        'click',
        function (event) {
            const node = event.target;
            // Save/Publish are <button type="submit">; the "Add rule/condition" buttons
            // are type="button", so they are intentionally not matched here.
            const button =
                node && node.closest
                    ? node.closest(
                          'button[type="submit"], input[type="submit"]'
                      )
                    : null;
            if (!button) {
                return;
            }
            const form =
                button.form || (button.closest && button.closest('form'));
            if (!isRoutingForm(form)) {
                return;
            }
            if (!validateConditions(form, payload)) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
        },
        true
    );

    target.addEventListener(
        'submit',
        function (event) {
            if (!isRoutingForm(event.target)) {
                return;
            }
            if (!validateConditions(event.target, payload)) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
        },
        true
    );
}

export function initConditionHelp(options) {
    const opts = options || {};
    const payload =
        opts.payload ||
        (typeof window !== 'undefined'
            ? window.ROUTING_SIGNAL_PAYLOAD
            : null) ||
        {};
    const scope = opts.root || document;

    wireAll(payload, scope);
    attachSubmitGuard(payload, scope);

    // Wagtail hydrates nested InlinePanel rows client-side *after* load, and "Add
    // rule/condition" inserts more rows later — none of which the one-shot scan above
    // sees. Without this observer the help never renders on those rows (the confirmed
    // ED-3 bug). Re-scan (idempotently) whenever nodes are added.
    const observeTarget =
        opts.root || (typeof document !== 'undefined' ? document.body : null);
    if (observeTarget && typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver(function () {
            wireAll(payload, scope);
        });
        observer.observe(observeTarget, { childList: true, subtree: true });
        return observer;
    }
    return null;
}

// Auto-run in the admin, but only once the payload global is present (the insert_editor_js
// hook sets it just before this script). Skipping when it's absent keeps the observer out
// of non-editor pages and unit tests, which drive the exported functions directly.
if (
    typeof document !== 'undefined' &&
    typeof window !== 'undefined' &&
    window.ROUTING_SIGNAL_PAYLOAD
) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initConditionHelp();
        });
    } else {
        initConditionHelp();
    }
}
