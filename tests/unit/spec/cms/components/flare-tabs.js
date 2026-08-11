/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import setupTabs, {
    TabsAutomatic
} from '../../../../../media/js/cms/components/flare-tabs.es6';

describe('flare-tabs.es6.js', function () {
    let container;

    function render(count, id) {
        id = id || 'hub';
        let markup = '<div class="fl-tabs-nav" role="tablist">';
        for (let i = 1; i <= count; i += 1) {
            markup +=
                '<button type="button" role="tab" id="fl-tab-' +
                id +
                '-' +
                i +
                '" aria-controls="fl-tab-panel-' +
                id +
                '-' +
                i +
                '">Tab ' +
                i +
                '</button>';
        }
        markup += '</div>';
        for (let i = 1; i <= count; i += 1) {
            markup +=
                '<div id="fl-tab-panel-' +
                id +
                '-' +
                i +
                '" role="tabpanel"></div>';
        }
        container = document.createElement('div');
        container.innerHTML = markup;
        document.body.appendChild(container);
    }

    function tabs() {
        return Array.from(container.querySelectorAll('[role=tab]'));
    }

    function selectedIndex() {
        return tabs().findIndex(function (tab) {
            return tab.getAttribute('aria-selected') === 'true';
        });
    }

    function panelHidden(index) {
        return container
            .querySelectorAll('[role=tabpanel]')
            [index].classList.contains('is-hidden');
    }

    afterEach(function () {
        if (container) {
            container.remove();
            container = null;
        }
    });

    describe('setupTabs', function () {
        it('should return an instance per tablist', function () {
            render(3, 'one');
            const second = document.createElement('div');
            second.innerHTML = '<div class="fl-tabs-nav" role="tablist"></div>';
            container.appendChild(second);

            const instances = setupTabs();

            // flare-browser-tabs.es6.js drives selection through these, so an
            // empty or undefined return would silently disable auto-selection.
            expect(instances.length).toEqual(2);
            expect(instances[0] instanceof TabsAutomatic).toBe(true);
        });

        it('should return an empty array when the page has no tablists', function () {
            expect(setupTabs()).toEqual([]);
        });
    });

    describe('initial state', function () {
        beforeEach(function () {
            render(3);
            setupTabs();
        });

        it('should select the first tab', function () {
            expect(selectedIndex()).toEqual(0);
        });

        it('should show only the first panel', function () {
            expect(panelHidden(0)).toBe(false);
            expect(panelHidden(1)).toBe(true);
            expect(panelHidden(2)).toBe(true);
        });

        it('should keep every tab in the keyboard tab order', function () {
            tabs().forEach(function (tab) {
                expect(tab.getAttribute('tabindex')).toBeNull();
            });
        });

        it('should not focus the first tab on load', function () {
            // Focusing here would scroll the page down to the tablist before the
            // visitor has done anything.
            expect(document.activeElement).not.toEqual(tabs()[0]);
        });
    });

    describe('interaction', function () {
        beforeEach(function () {
            render(3);
            setupTabs();
        });

        function press(key, index) {
            tabs()[index].dispatchEvent(
                new KeyboardEvent('keydown', { key: key, bubbles: true })
            );
        }

        it('should select a clicked tab', function () {
            tabs()[2].click();

            expect(selectedIndex()).toEqual(2);
            expect(panelHidden(0)).toBe(true);
            expect(panelHidden(2)).toBe(false);
        });

        it('should move to the next tab on ArrowRight', function () {
            press('ArrowRight', 0);
            expect(selectedIndex()).toEqual(1);
        });

        it('should wrap to the first tab from the last on ArrowRight', function () {
            tabs()[2].click();
            press('ArrowRight', 2);
            expect(selectedIndex()).toEqual(0);
        });

        it('should move to the previous tab on ArrowLeft', function () {
            tabs()[2].click();
            press('ArrowLeft', 2);
            expect(selectedIndex()).toEqual(1);
        });

        it('should wrap to the last tab from the first on ArrowLeft', function () {
            press('ArrowLeft', 0);
            expect(selectedIndex()).toEqual(2);
        });

        it('should jump to the first tab on Home and the last on End', function () {
            press('End', 0);
            expect(selectedIndex()).toEqual(2);
            press('Home', 2);
            expect(selectedIndex()).toEqual(0);
        });

        it('should focus the tab it moves to by keyboard', function () {
            press('ArrowRight', 0);
            expect(document.activeElement).toEqual(tabs()[1]);
        });
    });

    describe('tabbing through the tablist', function () {
        beforeEach(function () {
            render(3);
            setupTabs();
        });

        it('should not change the selection when a tab merely receives focus', function () {
            tabs()[2].focus();

            expect(selectedIndex()).toEqual(0);
            expect(panelHidden(0)).toBe(false);
            expect(panelHidden(2)).toBe(true);
        });

        it('should not swallow Enter, so a focused tab can be activated', function () {
            const tab = tabs()[2];
            const event = new KeyboardEvent('keydown', {
                key: 'Enter',
                bubbles: true,
                cancelable: true
            });
            tab.dispatchEvent(event);

            expect(event.defaultPrevented).toBe(false);
        });

        it('should not swallow Space, so a focused tab can be activated', function () {
            const event = new KeyboardEvent('keydown', {
                key: ' ',
                bubbles: true,
                cancelable: true
            });
            tabs()[2].dispatchEvent(event);

            expect(event.defaultPrevented).toBe(false);
        });

        it('should select a tab activated by keyboard', function () {
            tabs()[2].focus();
            tabs()[2].click();

            expect(selectedIndex()).toEqual(2);
            expect(panelHidden(2)).toBe(false);
        });

        it('should still consume the arrow keys it handles', function () {
            const event = new KeyboardEvent('keydown', {
                key: 'ArrowRight',
                bubbles: true,
                cancelable: true
            });
            tabs()[0].dispatchEvent(event);

            expect(event.defaultPrevented).toBe(true);
        });
    });

    describe('setSelectedTab', function () {
        it('should not move focus when asked not to', function () {
            render(3);
            const instance = setupTabs()[0];

            instance.setSelectedTab(tabs()[2], false);

            expect(selectedIndex()).toEqual(2);
            expect(document.activeElement).not.toEqual(tabs()[2]);
        });

        it('should tolerate a tab whose panel is missing', function () {
            // Panels and tabs are rendered by separate loops in tabs.html, so a
            // mismatch is possible in malformed content.
            render(1);
            container.querySelector('[role=tabpanel]').remove();

            expect(function () {
                setupTabs();
            }).not.toThrow();
        });
    });
});
