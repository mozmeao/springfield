/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import {
    placeDraftsharingButton,
    createSharingLink
} from '../../../../../media/js/cms/wagtailadmin-translation-draftsharing.es6.js';

const BUTTON_HTML = `<button type="button" class="button" data-translation-draftsharing
    data-url="/cms-admin/translation-draftsharing/37/">
        <svg></svg>
        Create draft sharing link
    </button>`;

function buildEditor(withTemplate) {
    const root = document.createElement('div');
    const template = withTemplate
        ? `<template id="translation-draftsharing-button">
            ${BUTTON_HTML}
          </template>`
        : '';
    root.innerHTML = `${template}
        <footer class="footer">
          <form method="POST">
            <nav class="actions actions--primary footer__container">
              <div data-w-dropdown-target="content"></div>
            </nav>
          </form>
        </footer>`;
    document.body.appendChild(root);
    return root;
}

describe('wagtailadmin-translation-draftsharing', function () {
    let root;

    afterEach(function () {
        if (root) {
            root.remove();
        }
        root = null;
    });

    describe('placeDraftsharingButton', function () {
        it('moves the button into the action menu list', function () {
            root = buildEditor(true);
            placeDraftsharingButton(root);
            const menu = root.querySelector(
                '[data-w-dropdown-target="content"]'
            );
            expect(
                menu.querySelector('[data-translation-draftsharing]')
            ).not.toBeNull();
        });

        it('does nothing when there is no button template', function () {
            root = buildEditor(false);
            placeDraftsharingButton(root);
            const menu = root.querySelector(
                '[data-w-dropdown-target="content"]'
            );
            expect(menu.children.length).toEqual(0);
        });

        it('does nothing when the footer has not mounted yet', function () {
            root = document.createElement('div');
            root.innerHTML = `<template id="translation-draftsharing-button">
                ${BUTTON_HTML}
                </template>`;
            document.body.appendChild(root);
            expect(function () {
                placeDraftsharingButton(root);
            }).not.toThrow();
        });

        it('does not add duplicate buttons', function () {
            root = buildEditor(true);
            placeDraftsharingButton(root);
            placeDraftsharingButton(root);
            placeDraftsharingButton(root);
            const menu = root.querySelector(
                '[data-w-dropdown-target="content"]'
            );
            expect(
                menu.querySelectorAll('[data-translation-draftsharing]').length
            ).toEqual(1);
        });

        it('re-inserts the button after the footer is re-rendered', function () {
            root = buildEditor(true);
            placeDraftsharingButton(root);
            root.querySelector('[data-w-dropdown-target="content"]').innerHTML =
                '';
            placeDraftsharingButton(root);
            const menu = root.querySelector(
                '[data-w-dropdown-target="content"]'
            );
            expect(
                menu.querySelectorAll('[data-translation-draftsharing]').length
            ).toEqual(1);
        });
    });

    describe('createSharingLink', function () {
        let writeText;

        beforeEach(function () {
            const config = document.createElement('script');
            config.id = 'wagtail-config';
            config.type = 'application/json';
            config.textContent = JSON.stringify({ CSRF_TOKEN: 'test-token' });
            document.body.appendChild(config);

            // Stub the copy step (never settles in headed Chrome)
            writeText = jasmine
                .createSpy('writeText')
                .and.returnValue(Promise.resolve());
            Object.defineProperty(navigator, 'clipboard', {
                value: { writeText },
                configurable: true
            });
        });

        afterEach(function () {
            document.getElementById('wagtail-config').remove();
            delete navigator.clipboard;
        });

        it('posts to the button url with the csrf token', async function () {
            root = buildEditor(true);
            placeDraftsharingButton(root);
            const button = root.querySelector(
                '[data-translation-draftsharing]'
            );
            spyOn(window, 'fetch').and.returnValue(
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ url: '/shared/abc/' })
                })
            );

            await createSharingLink(button);

            const [url, options] = window.fetch.calls.mostRecent().args;
            expect(url).toEqual('/cms-admin/translation-draftsharing/37/');
            expect(options.method).toEqual('POST');
            expect(options.headers['X-CSRFToken']).toEqual('test-token');
        });

        it('copies the returned url to the clipboard', async function () {
            root = buildEditor(true);
            placeDraftsharingButton(root);
            const button = root.querySelector(
                '[data-translation-draftsharing]'
            );
            const shareURL = '/shared/abc/';
            spyOn(window, 'fetch').and.returnValue(
                Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ url: shareURL })
                })
            );

            await createSharingLink(button);

            expect(writeText).toHaveBeenCalledWith(
                window.location.origin + shareURL
            );
            expect(button.textContent).toContain('Copied!');
        });

        it('restores the button icon and label when the request fails', async function () {
            root = buildEditor(true);
            placeDraftsharingButton(root);
            const button = root.querySelector(
                '[data-translation-draftsharing]'
            );
            const original = button.textContent;
            spyOn(window, 'fetch').and.returnValue(
                Promise.resolve({ ok: false })
            );

            await createSharingLink(button);

            expect(button.textContent).toEqual(original);
            expect(button.querySelector('svg')).not.toBeNull();
            expect(button.disabled).toBeFalse();
        });
    });
});
