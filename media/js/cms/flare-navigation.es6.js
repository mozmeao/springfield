/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Sticky header
import Headroom from 'headroom.js';
import { createFocusTrap } from 'focus-trap';

(function () {
    const headerEl = document.querySelector('.fl-header.enable-sticky');

    if (headerEl) {
        const headroomInstance = new Headroom(headerEl, {
            classes: {
                pinned: 'headroom-pinned',
                unpinned: 'headroom-unpinned',
                notTop: 'headroom-not-top',
                notBottom: 'headroom-not-bottom'
            }
        });
        headroomInstance.init();
    }

    // Hamburger menu
    const buttonEl = document.querySelector('.fl-show-mobile-menu');
    const mobileNavEl = document.querySelector('.fl-nav');
    const trap = createFocusTrap(headerEl);

    buttonEl.addEventListener('click', function (e) {
        e.preventDefault();
        const mobileNavIsOpen = e.target.classList.contains('is-open');
        const elements = [e.target, mobileNavEl];

        if (mobileNavIsOpen) {
            elements.forEach(function (el) {
                el.classList.remove('is-open');
            });
            document.body.classList.remove('fl-modal-open');
            mobileNavEl.removeAttribute('role');
            mobileNavEl.removeAttribute('aria-modal');
            trap.deactivate();
        } else {
            elements.forEach(function (el) {
                el.classList.add('is-open');
            });
            document.body.classList.add('fl-modal-open');
            mobileNavEl.setAttribute('role', 'dialog');
            mobileNavEl.setAttribute('aria-modal', 'true');
            trap.activate();
        }
    });

    // Menu panels

    const menuCategories = document.querySelectorAll('.fl-menu-category');

    // mouse is being used
    menuCategories.forEach(function (category) {
        category.addEventListener('mouseover', function () {
            category.classList.add('is-active');
        });
        category.addEventListener('mouseout', function () {
            category.classList.remove('is-active');
        });
    });

    const menuTitles = document.querySelectorAll('.fl-menu-title');

    // keyboard is being used
    menuTitles.forEach(function (title) {
        // when leaving the last link of a menu, close all menus
        const menuLinks = title
            .closest('.fl-menu-category')
            .querySelectorAll('a');
        menuLinks[menuLinks.length - 1].addEventListener(
            'keydown',
            function (event) {
                if (event.key === 'Tab' && !event.shiftKey) {
                    menuCategories.forEach(function (category) {
                        category.classList.remove('is-active');
                    });
                }
            }
        );

        // when clicking or pressing enter, toggle the menu
        title.addEventListener('click', function (event) {
            event.preventDefault();

            const menuPanel = event.target.closest('.fl-menu-category');

            if (menuPanel.classList.contains('is-active')) {
                menuPanel.classList.remove('is-active');
            } else {
                menuPanel.classList.add('is-active');
            }
        });
    });

    const menuPanelCloseButtons = document.querySelectorAll(
        '.fl-menu-close-button'
    );

    menuPanelCloseButtons.forEach(function (button) {
        button.addEventListener('click', function (event) {
            event.preventDefault();
            const menuPanel = event.target.closest('.fl-menu-category');
            menuPanel.classList.remove('is-active');
        });
    });
})();
