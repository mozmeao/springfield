/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Sticky header
import { createFocusTrap } from 'focus-trap';

(function () {
    const desktopMediaQuery = window.matchMedia('(min-width: 900px)');

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

    const nav = document.querySelector('.fl-nav');

    // Menu panels
    const menuCategories = document.querySelectorAll('.fl-menu-category');

    for (const category of menuCategories) {
        const title = category.querySelector('.fl-menu-title');
        const panel = category.querySelector('.fl-menu-panel');

        /* ESSENTIAL SEMANTICS: Convert link menu titles to buttons */
        if (title.matches('a') && desktopMediaQuery.matches) {
            if (title.hasAttribute('href')) {
                title.dataset.href = title.getAttribute('href');
                title.removeAttribute('href');
            }
            title.setAttribute('tabindex', 0);
            title.setAttribute('role', 'button');
            title.setAttribute('aria-expanded', 'false');
            title.setAttribute('aria-controls', panel.id);
        }
    }

    // Perform initial event listener setup
    setupEventListeners();

    desktopMediaQuery.addEventListener('change', (event) => {
        const isDesktop = event.matches;
        const titleButtons = document.querySelectorAll(
            '.fl-menu-category .fl-menu-title'
        );

        for (const titleButton of titleButtons) {
            if (isDesktop) {
                titleButton.removeAttribute('href');
                titleButton.setAttribute('tabindex', 0);
                titleButton.setAttribute('role', 'button');
                titleButton.setAttribute('aria-expanded', 'false');
                titleButton.setAttribute(
                    'aria-controls',
                    getPanelForCategory(getCategory(titleButton)).id
                );
            } else {
                if (titleButton.dataset.href) {
                    titleButton.setAttribute('href', titleButton.dataset.href);
                }
                titleButton.removeAttribute('tabindex');
                titleButton.removeAttribute('role');
                titleButton.removeAttribute('aria-expanded');
                titleButton.removeAttribute('aria-controls');
            }
        }

        setupEventListeners();
    });

    /* Sets up and tears down delegated event listeners based on desktop media query */
    function setupEventListeners() {
        if (desktopMediaQuery.matches) {
            nav.addEventListener('click', handleCategoryToggle);
            nav.addEventListener('keydown', handleNonLinkAnchorClick);
            nav.addEventListener('keyup', handleNonLinkAnchorClick);
            nav.addEventListener('blur', handleAutoClose, true);
            nav.addEventListener('mouseenter', handleCategoryHoverReveal, true);
            document.addEventListener('keydown', handleDismissActiveCategory);
        } else {
            nav.removeEventListener('click', handleCategoryToggle);
            nav.removeEventListener('keydown', handleNonLinkAnchorClick);
            nav.removeEventListener('keyup', handleNonLinkAnchorClick);
            nav.removeEventListener('blur', handleAutoClose, true);
            nav.removeEventListener(
                'mouseenter',
                handleCategoryHoverReveal,
                true
            );
            document.removeEventListener(
                'keydown',
                handleDismissActiveCategory
            );
        }
    }

    /* DELEGATED EVENT HANDLERS */

    function handleNonLinkAnchorClick(event) {
        if (event.type === 'keydown' && event.key === ' ') {
            event.target.closest('[role="button"]').click();
        }
        if (event.type === 'keyup' && event.key === 'Enter') {
            event.target.closest('[role="button"]').click();
        }
    }

    /**
     * Handles toggling panels on click.
     */
    function handleCategoryToggle(event) {
        if (!event.target.closest('.fl-menu-title')) return;
        const category = getCategory(event.target);
        const activeCategory = getActiveCategory();
        if (category !== activeCategory) {
            toggleCategory(getActiveCategory(), false);
        }
        toggleCategory(category);
    }

    /**
     * Dismisses an active panel when the Escape key is pressed
     */
    function handleDismissActiveCategory(event) {
        if (event.key === 'Escape') {
            const activeCategory = getActiveCategory();

            if (!activeCategory) return;

            const title = getTitleForCategory(activeCategory);
            const focusedElement = document.activeElement;

            toggleCategory(activeCategory, false);

            if (activeCategory.contains(focusedElement)) {
                title.focus();
            }
        }
    }

    /**
     * Auto-closes open panels on blur.
     */
    function handleAutoClose(event) {
        const category = getCategory(event.target);
        const panel = getPanelForCategory(category);
        if (!panel.contains(event.relatedTarget)) {
            toggleCategory(category, false);
        }
    }

    function handleCategoryHoverReveal(event) {
        // If a menu has been opened with other interaction types, ignore.
        if (!event.target.matches('.fl-menu-category:not(.is-active)')) return;

        toggleCategory(getActiveCategory(), false);
        toggleCategory(event.target, true);

        event.target.addEventListener(
            'mouseleave',
            (event) => {
                toggleCategory(getCategory(event.target), false);
            },
            { once: true }
        );
    }

    /* TOGGLING LOGIC */

    /* Toggles panel visibility and trigger aria-expanded */
    function toggleCategory(
        category,
        force = category && !category.classList.contains('is-active')
    ) {
        if (!category) return;
        const title = getTitleForCategory(category);
        category.classList.toggle('is-active', force);
        title.setAttribute('aria-expanded', force ? 'true' : 'false');
    }

    /* RELATIVE QUERY HELPERS */

    function getActiveCategory() {
        return document.querySelector('.fl-menu-category.is-active');
    }

    function getCategory(node) {
        return node.closest('.fl-menu-category');
    }

    function getPanelForCategory(category) {
        return category.querySelector('.fl-menu-panel');
    }

    function getTitleForCategory(category) {
        return category.querySelector('.fl-menu-title');
    }
})();
