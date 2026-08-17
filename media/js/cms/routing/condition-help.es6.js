/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/**
 * User Routing — dynamic condition help text in the Wagtail admin.
 *
 * When an author picks a signal in a routing condition, this surfaces the valid values
 * beneath the expected-value field: the enumerated set for enum signals, or a type hint
 * plus the operator meanings for the rest. Everything human-readable comes from
 * `window.ROUTING_SIGNAL_PAYLOAD` (the registry, localized server-side), so the
 * help can never drift from the evaluator and needs no English literals here.
 */

const HELP_CLASSNAME = 'routing-condition-help';
// Added to the help element (and aria-invalid on the field) when a value fails
// pre-submit validation, so the same help line doubles as the correction guidance.
const ERROR_CLASSNAME = 'routing-condition-help--invalid';
// Added to a rule's conditions panel while its "match all" box is ticked, so the author can
// see the conditions are inert. Styled in the admin CSS.
const IGNORED_CLASSNAME = 'routing-conditions--ignored';
// Wagtail's wrapper class for a nested InlinePanel — the conditions panel inside a rule.
const NESTED_PANEL_CLASSNAME = 'w-panel--nested';
// Flag set on a wired signal <select> so re-scans never double-bind it.
const BOUND_FLAG = 'springfieldRoutingBound';
// Flag set on a wired "match all" checkbox, same reason as BOUND_FLAG.
const MATCH_ALL_BOUND_FLAG = 'springfieldRoutingMatchAllBound';
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
    } else if (meta.exampleValues && meta.exampleValues.length) {
        // The legal set is far larger than is useful to read (any language code), so show
        // a representative subset. `meta.hint` says these are examples, not the whole set.
        parts.push(meta.hint + ' ' + joinCapped(meta.exampleValues));
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
    // Restrict the operator dropdown to the operators legal for the chosen signal:
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
    // Set-membership values are entered one-per-line and/or comma-separated, so split on
    // both (matches the Python RoutingCondition.expected_values() convention).
    return String(value)
        .split(/[\n,]/)
        .map((entry) => entry.trim())
        .filter(Boolean);
}

export function classifyValue(meta, operator, value) {
    // Grade a condition value against RoutingCondition.clean():
    //   'ok'   — acceptable.
    //   'hard' — the server would reject it, it would silently mis-route (a malformed
    //            boolean like "yess" → false), or it could never match anything (a value
    //            outside a signal's complete set). Blocks the save when the field is
    //            on-screen; a row on an inactive tab still falls through to the server so
    //            Wagtail owns error/tab routing natively.
    if (!meta) {
        return 'ok'; // unknown/blank signal: leave it to the server
    }
    // Operator must be legal for the signal (filterOperators narrows the dropdown; this backstops it).
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
    // Known-set string (locale/country): the set is the signal's *complete* domain, so an
    // off-list value can never match anything at runtime — the rule would be silently dead.
    // Treated exactly like an enum; these are enums in all but declaration.
    if (meta.values && meta.values.length) {
        const parts = isMembership ? splitList(value) : [raw];
        const allMembers =
            parts.length > 0 &&
            parts.every((part) => meta.values.indexOf(part) !== -1);
        return allMembers ? 'ok' : 'hard';
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
    // The "is this value acceptable?" check that drives the inline red hint. Whether a
    // failure also *blocks the save* is a separate question — see validateConditionRow,
    // which additionally requires the field to be visible.
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

// --- match-all rules ignore their conditions -------------------------------
//
// The serializer drops conditions from a match-all rule, so the editor has to show that
// rather than leaving an author looking at conditions they wrote which will never be
// consulted. The *explanation* is server-rendered and translated (the checkbox's help text
// and the conditions panel's); all this adds is the live state.

function matchAllCheckboxFor(select, root) {
    // "…-conditions-3-signal" belongs to the rule whose checkbox is "…-match_all".
    const name = select.getAttribute('name') || '';
    const checkboxName = name.replace(/-conditions-\d+-signal$/, '-match_all');
    if (checkboxName === name) {
        return null;
    }
    return root.querySelector('[name="' + checkboxName + '"]');
}

function conditionIsIgnored(select, root) {
    const checkbox = matchAllCheckboxFor(select, root);
    return !!(checkbox && checkbox.checked);
}

function conditionsPanelFor(checkbox, root) {
    // Derived from the formset naming rather than the surrounding markup: Wagtail wraps a
    // nested InlinePanel's rows in "id_<prefix>-FORMS", and the panel around that carries
    // the heading and the Add button. Falling back to the rows alone keeps the cue working
    // if that outer wrapper is ever restyled.
    const name = checkbox.getAttribute('name') || '';
    const formsId = 'id_' + name.replace(/-match_all$/, '-conditions-FORMS');
    const forms = root.querySelector('[id="' + formsId + '"]');
    if (!forms) {
        return null;
    }
    const panel =
        typeof forms.closest === 'function'
            ? forms.closest('.' + NESTED_PANEL_CLASSNAME)
            : null;
    return panel || forms;
}

export function syncIgnoredConditions(checkbox, root) {
    const scope = root || document;
    const panel = conditionsPanelFor(checkbox, scope);
    if (!panel) {
        return null;
    }
    if (checkbox.checked) {
        panel.classList.add(IGNORED_CLASSNAME);
    } else {
        panel.classList.remove(IGNORED_CLASSNAME);
    }
    return panel;
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
    // Skip conditions the server will ignore anyway: blocking a save on a value that has
    // no effect would be the editor contradicting itself twice over.
    if (conditionIsIgnored(select, scope)) {
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
    // Surface the red hint inline for any failure (on blur/change and on a blocked submit).
    setConditionError(select, payload, scope, status !== 'ok');
    // Only block when the field is actually on-screen: a row on an inactive tab falls
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
        help.id =
            (expected.id || expected.getAttribute('name')) + '-routing-help';
        expected.parentNode.appendChild(help);
        // Screen readers announce this alongside the field's own description, not only
        // its aria-invalid state — merge rather than overwrite any existing value.
        const described = (expected.getAttribute('aria-describedby') || '')
            .split(/\s+/)
            .filter(Boolean);
        if (described.indexOf(help.id) === -1) {
            described.push(help.id);
            expected.setAttribute('aria-describedby', described.join(' '));
        }
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
        // filterOperators first: it can replace the selected operator (e.g. resetting to
        // the new signal's default), and the help text below reads that operator — render
        // after, or the comma hint reflects the operator that's about to be replaced.
        filterOperators(select, payload, scope);
        renderConditionHelp(select, payload, scope);
    });
    // Revalidate when the operator changes too — the comma-separated hint appears/disappears
    // with in / not in, and a value that was invalid for the old operator (or vice versa)
    // needs its error state recomputed, not just the help text.
    const operatorSelect = operatorFieldFor(select, scope);
    if (operatorSelect) {
        operatorSelect.addEventListener('change', function () {
            validateConditionRow(select, payload, scope);
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
    // its operator dropdown already scoped (and its saved operator preserved) — filtered
    // before the help text reads it, same reasoning as the change handler above.
    filterOperators(select, payload, scope);
    renderConditionHelp(select, payload, scope);
}

function revalidateRuleConditions(checkbox, payload, scope) {
    const selects = scope.querySelectorAll('select[name$="-signal"]');
    Array.prototype.forEach.call(selects, function (select) {
        if (matchAllCheckboxFor(select, scope) === checkbox) {
            validateConditionRow(select, payload, scope);
        }
    });
}

function wireMatchAll(checkbox, payload, scope) {
    // Idempotent, like wireSelect: the observer re-scans on every DOM change.
    if (checkbox.dataset[MATCH_ALL_BOUND_FLAG] === '1') {
        return;
    }
    checkbox.dataset[MATCH_ALL_BOUND_FLAG] = '1';
    checkbox.addEventListener('change', function () {
        syncIgnoredConditions(checkbox, scope);
        // Ticking clears the red hints on the conditions just made inert; unticking brings
        // back any that are genuinely wrong. Row-by-row rather than validateConditions(),
        // which moves focus to the first invalid field — jarring on a checkbox click.
        revalidateRuleConditions(checkbox, payload, scope);
    });
    // Initial pass, so a saved match-all rule opens with its conditions already dimmed.
    syncIgnoredConditions(checkbox, scope);
}

function wireAll(payload, scope) {
    const selects = scope.querySelectorAll('select[name$="-signal"]');
    Array.prototype.forEach.call(selects, function (select) {
        wireSelect(select, payload, scope);
    });
    const checkboxes = scope.querySelectorAll(
        'input[type="checkbox"][name$="-match_all"]'
    );
    Array.prototype.forEach.call(checkboxes, function (checkbox) {
        wireMatchAll(checkbox, payload, scope);
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
    // server error. The Wagtail page form is `novalidate` and saves via a Stimulus
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
    // bug). Re-scan (idempotently) whenever nodes are added.
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
