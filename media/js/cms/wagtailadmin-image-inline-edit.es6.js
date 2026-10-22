/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Saves a row of the image listing from its inline form and swaps the server's re-rendered
 * cells into the row. Rows with unsaved edits are marked, and leaving the page or replacing
 * the results through search or filters asks for confirmation first.
 *
 * A row's inputs sit in separate table cells and join the row's <form> through their `form`
 * attribute, so `new FormData(form)` and `input.form` both include them.
 */

const FORM_SELECTOR = '[data-inline-image-form]';
const STATUS_SELECTOR = '[data-inline-image-status]';
const DIRTY_ATTRIBUTE = 'data-inline-dirty';

function setStatus(row, message) {
    const status = row.querySelector(STATUS_SELECTOR);
    if (status) {
        status.textContent = message;
    }
}

function hasUnsavedRows() {
    return document.querySelector(`tr[${DIRTY_ATTRIBUTE}]`) !== null;
}

function markRowDirty(event) {
    const cell = event.target.closest('.inline-edit-cell');
    const row = cell && cell.closest('tr');
    if (!row || !row.querySelector(FORM_SELECTOR)) {
        return;
    }
    if (!row.hasAttribute(DIRTY_ATTRIBUTE)) {
        row.setAttribute(DIRTY_ATTRIBUTE, '');
        setStatus(row, 'Unsaved changes');
    }
}

function replaceCells(row, responseHtml) {
    const focusedElement = row.contains(document.activeElement)
        ? document.activeElement
        : null;
    const focusedId = focusedElement && focusedElement.id;
    const template = document.createElement('template');
    template.innerHTML = responseHtml;
    template.content
        .querySelectorAll('[data-inline-cell]')
        .forEach((newCell) => {
            const oldCell = row.querySelector(
                `[data-inline-cell="${newCell.dataset.inlineCell}"]`
            );
            if (oldCell) {
                oldCell.replaceWith(newCell);
            }
        });
    if (!focusedElement) {
        return;
    }
    const firstError = row.querySelector('.error-message');
    const target = firstError
        ? firstError
              .closest('.inline-edit-cell')
              .querySelector('input, textarea')
        : (focusedId && document.getElementById(focusedId)) ||
          row.querySelector('button[type="submit"]');
    if (target) {
        target.focus();
    }
}

// Re-sets the server's status text so screen readers announce it again.
function announceStatus(row) {
    const status = row.querySelector(STATUS_SELECTOR);
    if (!status) {
        return;
    }
    const message = status.textContent;
    status.textContent = '';
    requestAnimationFrame(() => {
        status.textContent = message;
    });
}

function serializeForm(form) {
    return new URLSearchParams(new FormData(form)).toString();
}

async function saveRow(event) {
    const form = event.target;
    if (!form.matches(FORM_SELECTOR)) {
        return;
    }
    event.preventDefault();

    const row = form.closest('tr');
    const button = form.querySelector('button[type="submit"]');
    const wagtailConfig = JSON.parse(
        document.getElementById('wagtail-config').textContent
    );
    const submittedData = serializeForm(form);
    button.disabled = true;

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            body: new URLSearchParams(submittedData),
            headers: {
                [wagtailConfig.CSRF_HEADER_NAME]: wagtailConfig.CSRF_TOKEN,
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        if (
            response.redirected ||
            (response.status !== 200 && response.status !== 400)
        ) {
            throw new Error(`Unexpected response ${response.status}`);
        }
        const responseHtml = await response.text();
        if (serializeForm(form) !== submittedData) {
            // Edited while saving: keep the newer edits, which are still unsaved.
            button.disabled = false;
            return;
        }
        replaceCells(row, responseHtml);
        announceStatus(row);
        if (response.ok) {
            row.removeAttribute(DIRTY_ATTRIBUTE);
        }
    } catch (error) {
        button.disabled = false;
        setStatus(row, "Couldn't save, try again");
    }
}

function confirmDiscardBeforeSwap(event) {
    if (
        hasUnsavedRows() &&
        // eslint-disable-next-line no-alert
        !window.confirm('Some images have unsaved changes. Discard them?')
    ) {
        event.preventDefault();
        // Wagtail's swap controller shows its spinner before dispatching this event and
        // doesn't clear it when the event is cancelled.
        document
            .querySelectorAll('[data-w-swap-loading-value="true"]')
            .forEach((element) => {
                element.setAttribute('data-w-swap-loading-value', 'false');
            });
    }
}

function warnBeforeUnload(event) {
    if (hasUnsavedRows()) {
        event.preventDefault();
        event.returnValue = '';
    }
}

document.addEventListener('input', markRowDirty);
document.addEventListener('change', markRowDirty);
// Wagtail's tag widget (tag-it) reports tag changes only through jQuery events, and also fires
// them while building a row's existing tags on load, which is not an edit.
if (window.jQuery) {
    window
        .jQuery(document)
        .on(
            'tagitaftertagadded tagitaftertagremoved',
            '.inline-edit-cell',
            (event, tagDetails) => {
                if (tagDetails && tagDetails.duringInitialization) {
                    return;
                }
                markRowDirty(event);
            }
        );
}
document.addEventListener('submit', saveRow);
document.addEventListener('w-swap:begin', confirmDiscardBeforeSwap);
window.addEventListener('beforeunload', warnBeforeUnload);
