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

export function buildHelpText(meta) {
    if (!meta) {
        return '';
    }
    // Values-first (ED-3): a closed value set is the most useful thing to show, so it
    // leads the help line for enum signals and for string signals with a known set
    // (locale / country). The lead-in (`hint`) is localized server-side.
    if (meta.enumValues && meta.enumValues.length) {
        const values = meta.enumValues
            .map((entry) => entry.label + ' (' + entry.value + ')')
            .join(', ');
        return meta.hint + ' ' + values;
    }
    if (meta.values && meta.values.length) {
        return meta.hint + ' ' + joinCapped(meta.values);
    }
    const operators = (meta.operators || [])
        .map((entry) => entry.label)
        .join(', ');
    return operators ? meta.hint + ' ' + operators : meta.hint;
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

export function validateExpectedValue(meta, operator, value) {
    // Mirror RoutingCondition.clean() on the client (ED-4) so a bad value is caught before
    // submit instead of bouncing to the Content tab. The server clean() stays the backstop.
    if (!meta) {
        return true; // unknown/blank signal: leave it to the server
    }
    // Operator must be legal for the signal (C25 filters the dropdown; this backstops it).
    if (operator && meta.operators) {
        const legal = meta.operators.map((entry) => entry.value);
        if (legal.indexOf(operator) === -1) {
            return false;
        }
    }
    const raw = String(
        value === undefined || value === null ? '' : value
    ).trim();
    if (!raw) {
        return false; // a condition always needs a value
    }
    const isMembership = MEMBERSHIP_OPERATORS.indexOf(operator) !== -1;
    // Enum / known-set string (locale, country): every value must be a member.
    let members = null;
    if (meta.enumValues && meta.enumValues.length) {
        members = meta.enumValues.map((entry) => entry.value);
    } else if (meta.values && meta.values.length) {
        members = meta.values;
    }
    if (members) {
        const parts = isMembership ? splitList(value) : [raw];
        return (
            parts.length > 0 &&
            parts.every((part) => members.indexOf(part) !== -1)
        );
    }
    if (meta.valueType === 'boolean') {
        return /^(true|false|1|0)$/i.test(raw);
    }
    if (meta.valueType === 'integer') {
        return /^-?\d+$/.test(raw);
    }
    if (meta.valueType === 'version') {
        // Accept bare / rv:-prefixed / dotted forms (matches normalizeVersion).
        return /^\d+(\.\d+)*$/.test(raw.replace(/^[^\d]*/, ''));
    }
    // Free-text string (utm_*): any non-empty value is acceptable.
    return true;
}

function setConditionError(select, payload, scope, hasError) {
    // Reuse the (localized) help line as the correction guidance; flag it + the field.
    const help = renderConditionHelp(select, payload, scope);
    if (help) {
        if (hasError) {
            help.classList.add(ERROR_CLASSNAME);
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

function validateConditionRow(select, payload, scope) {
    // Skip rows being deleted — they won't be saved.
    const del = siblingFieldFor(select, scope, '-DELETE');
    if (del && del.checked) {
        setConditionError(select, payload, scope, false);
        return true;
    }
    const operatorSelect = operatorFieldFor(select, scope);
    const expected = expectedFieldFor(select, scope);
    const valid = validateExpectedValue(
        payload[select.value],
        operatorSelect ? operatorSelect.value : '',
        expected ? expected.value : ''
    );
    setConditionError(select, payload, scope, !valid);
    return valid;
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
    let help = expected.parentNode.querySelector('.' + HELP_CLASSNAME);
    if (!help) {
        help = document.createElement('p');
        help.className = HELP_CLASSNAME;
        expected.parentNode.appendChild(help);
    }
    help.textContent = buildHelpText(payload[select.value]);
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

function findEditForm(scope) {
    if (scope.tagName === 'FORM') {
        return scope;
    }
    if (scope.querySelector) {
        return (
            scope.querySelector('#page-edit-form') ||
            scope.querySelector('form')
        );
    }
    return null;
}

function attachSubmitGuard(payload, scope) {
    // Validate every condition value before the page form submits, so an illegal value is
    // caught inline instead of round-tripping to a server error that bounces to the
    // Content tab (ED-4). Bound once per form; capture phase so it runs before Wagtail's.
    const form = findEditForm(scope);
    if (!form || form.dataset[SUBMIT_GUARD_FLAG] === '1') {
        return;
    }
    form.dataset[SUBMIT_GUARD_FLAG] = '1';
    form.addEventListener(
        'submit',
        function (event) {
            if (!validateConditions(form, payload)) {
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
