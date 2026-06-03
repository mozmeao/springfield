/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Sticky header
import { createFocusTrap } from 'focus-trap';

(function () {
    const headerEl = document.querySelector('.fl-header.enable-sticky');

    if (headerEl) {
        const sentinel = document.createElement('div');
        sentinel.className = 'fl-header-sentinel';
        sentinel.setAttribute('aria-hidden', 'true');
        headerEl.parentNode.insertBefore(sentinel, headerEl);

        const observer = new IntersectionObserver(function (entries) {
            headerEl.classList.toggle(
                'is-scrolled',
                !entries[0].isIntersecting
            );
        });
        observer.observe(sentinel);
    }

    // Hamburger menu
    const buttonEl = document.querySelector('.fl-show-mobile-menu');
    const mobileNavEl = document.querySelector('.fl-nav');
    const trap = createFocusTrap(headerEl);

    if (buttonEl && mobileNavEl) {
        buttonEl.addEventListener('click', function (e) {
            e.preventDefault();
            const mobileNavIsOpen =
                e.currentTarget.classList.contains('is-open');
            const elements = [e.currentTarget, mobileNavEl];

            if (mobileNavIsOpen) {
                elements.forEach(function (el) {
                    el.classList.remove('is-open');
                });
                document.body.classList.remove('fl-modal-open');
                trap.deactivate();
            } else {
                elements.forEach(function (el) {
                    el.classList.add('is-open');
                });
                document.body.classList.add('fl-modal-open');
                trap.activate();
            }
        });
    }

    // Menu panels
    const menuCategories = document.querySelectorAll('.fl-menu-category');

    for (const category of menuCategories) {
        let title = category.querySelector('.fl-menu-title');
        const panel = category.querySelector('.fl-menu-panel');

        /* ESSENTIAL SEMANTICS: Convert link menu titles to buttons */
        if (title.matches(':any-link')) {
            const button = document.createElement('button');
            button.append(...title.childNodes);
            button.classList.add(...title.classList);
            button.type = 'button';
            button.ariaExpanded = 'false';
            button.setAttribute('aria-controls', panel.id);
            button.dataset.testid = title.dataset.testid;
            title.replaceWith(button);
            title = button;
        }

        /* ESSENTIAL INTERACTION */

        /* Menu titles toggle their associated panels */
        title.addEventListener('click', () => {
            const activeCategory = getActiveCategory();
            if (category !== activeCategory) {
                toggleCategory(getActiveCategory(), false);
            }
            toggleCategory(category);
        });

        /* BONUS INTERACTION */

        /* Panels auto-close when focus leaves */
        panel.addEventListener(
            'blur',
            (event) => {
                if (!panel.contains(event.relatedTarget)) {
                    toggleCategory(getActiveCategory(), false);
                }
            },
            true
        );

        /* Reveal menu on hover */
        category.addEventListener('mouseenter', () => {
            // If a menu has been opened with other interaction types, ignore.
            if (category.matches('.is-active')) return;

            toggleCategory(getActiveCategory(), false);
            toggleCategory(category, true);

            /* This gets added once and is called once */
            category.addEventListener(
                'mouseleave',
                () => toggleCategory(category, false),
                { once: true }
            );
        });
    }

    /* Closes the active panel and returns focus to the title (if focus was within the panel) */
    document.addEventListener('keyup', (event) => {
        if (event.key === 'Escape') {
            const activeCategory = getActiveCategory();

            if (!activeCategory) return;

            const activeCategoryTitle =
                activeCategory.querySelector('.fl-menu-title');
            const focusedElement = document.activeElement;

            toggleCategory(activeCategory, false);

            if (activeCategory.contains(focusedElement)) {
                activeCategoryTitle.focus();
            }
        }
    });

    function getActiveCategory() {
        return document.querySelector('.fl-menu-category.is-active');
    }

    /* Toggles panel visibility and trigger aria-expanded */
    function toggleCategory(
        category,
        force = category && !category.classList.contains('is-active')
    ) {
        if (!category) return;
        const title = category.querySelector('.fl-menu-title');
        category.classList.toggle('is-active', force);
        title.setAttribute('aria-expanded', force ? 'true' : 'false');
    }
})();
