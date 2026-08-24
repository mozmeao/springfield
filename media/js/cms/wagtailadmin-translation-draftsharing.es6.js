/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/*
 * Places the draft sharing button into the translation editor's action menu.
 *
 * The editor footer is rendered by React from a fixed set of props, so there is no
 * server-side hook for adding an action to it. The button is rendered into a
 * `<template>` element by the `translation_draftsharing_button` tag and moved into
 * the menu here, then re-inserted whenever React rebuilds the footer.
 */

const TEMPLATE_ID = 'translation-draftsharing-button';
const MENU_SELECTOR =
    'footer .actions--primary [data-w-dropdown-target="content"]';
const BUTTON_SELECTOR = '[data-translation-draftsharing]';

function getCsrfToken() {
    const config = document.querySelector('script#wagtail-config');
    return config ? JSON.parse(config.textContent).CSRF_TOKEN : '';
}

export async function createSharingLink(button) {
    const labelNode = button.lastChild;
    const originalLabel = labelNode.textContent;
    button.disabled = true;
    labelNode.nodeValue = 'Copying...';

    try {
        const response = await window.fetch(button.dataset.url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                Accept: 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCsrfToken()
            }
        });
        if (!response.ok) {
            labelNode.nodeValue = originalLabel;
            button.disabled = false;
            return;
        }

        const data = await response.json();
        const url = window.location.origin + data.url;
        try {
            await navigator.clipboard.writeText(url);
            labelNode.nodeValue = 'Copied!';
        } catch (error) {
            labelNode.nodeValue = 'Created!';
            document.dispatchEvent(
                new CustomEvent('w-messages:add', {
                    detail: {
                        clear: true,
                        text: 'Draft sharing URL: ' + url,
                        type: 'success'
                    }
                })
            );
        }
        window.setTimeout(function () {
            labelNode.nodeValue = originalLabel;
            button.disabled = false;
        }, 3000);
    } catch (error) {
        labelNode.nodeValue = originalLabel;
        button.disabled = false;
    }
}

export function placeDraftsharingButton(root) {
    const template = document.querySelector('#' + TEMPLATE_ID);
    if (!template) {
        return null;
    }
    const scope = root || document;

    // The w-dropdown controller moves this node into a Tippy popper, so it has to be
    // looked up again on every pass.
    const menu = scope.querySelector(MENU_SELECTOR);
    if (!menu || menu.querySelector(BUTTON_SELECTOR)) {
        return null;
    }

    menu.appendChild(template.content.cloneNode(true));
    const button = menu.querySelector(BUTTON_SELECTOR);
    button.addEventListener('click', function (event) {
        event.preventDefault();
        createSharingLink(button);
    });
    return button;
}

export function initTranslationDraftsharing(options) {
    const opts = options || {};
    const root = opts.root || document.querySelector('.js-translation-editor');
    if (!root) {
        return null;
    }

    placeDraftsharingButton(root);

    if (typeof MutationObserver === 'undefined') return null;
    const observer = new MutationObserver(function () {
        placeDraftsharingButton(root);
    });
    observer.observe(root, { childList: true, subtree: true });
    return observer;
}

// Auto-run only when there is a button (so there is something to share). Skips otherwise.
if (typeof document !== 'undefined' && document.getElementById(TEMPLATE_ID)) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () {
            initTranslationDraftsharing();
        });
    } else {
        initTranslationDraftsharing();
    }
}
