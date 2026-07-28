/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

// Sticky header
import { createFocusTrap } from 'focus-trap';

(function () {
    /* Custom media: --viewport-md-up */
    const viewportMdUpQuery = window.matchMedia('(min-width: 900px)');

    const headerEl = document.querySelector('.fl-header.enable-sticky');
    const nav = document.querySelector('.fl-nav');

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
    const trap = createFocusTrap(headerEl);

    if (buttonEl && nav) {
        buttonEl.addEventListener('click', function (e) {
            e.preventDefault();
            const mobileNavIsOpen =
                e.currentTarget.classList.contains('is-open');
            const elements = [e.currentTarget, nav];

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
        const title = category.querySelector('.fl-menu-title');

        if (!getPanelForCategory(category)) continue;

        /* ESSENTIAL SEMANTICS: Convert anchor menu titles to buttons */
        if (title.matches('a') && viewportMdUpQuery.matches) {
            applyButtonSemanticsToAnchor(title);
        }
    }

    // Perform initial event listener setup
    setupEventListeners();

    viewportMdUpQuery.addEventListener('change', (event) => {
        const menuTitles = document.querySelectorAll(
            '.fl-menu-category .fl-menu-title'
        );

        for (const title of menuTitles) {
            if (!getPanelForCategory(getCategory(title))) continue;

            if (event.matches) {
                applyButtonSemanticsToAnchor(title);
            } else {
                removeButtonSemanticsFromAnchor(title);
            }
        }

        setupEventListeners();
    });

    /* Sets up and tears down delegated event listeners based on desktop media query */
    function setupEventListeners() {
        if (viewportMdUpQuery.matches) {
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
        const button = event.target.closest('[role="button"]');

        if (!button) return;

        if (event.type === 'keydown' && event.key === ' ') {
            event.preventDefault();
            button.click();
        }
        if (event.type === 'keyup' && event.key === 'Enter') {
            button.click();
        }
    }

    /**
     * Handles toggling panels on click.
     */
    function handleCategoryToggle(event) {
        if (!event.target.closest('.fl-menu-title')) return;
        const category = getCategory(event.target);

        if (!getPanelForCategory(category)) return;

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
        const panel = category && getPanelForCategory(category);

        if (!panel) return;

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

    /* SEMANTIC SETUP */

    /* Applies button semantics to menu title (anchor) */
    function applyButtonSemanticsToAnchor(anchor) {
        if (anchor.hasAttribute('href')) {
            anchor.dataset.href = anchor.getAttribute('href');
            // Remove the link semantics
            anchor.removeAttribute('href');
        }
        // Remove button semantics (apply link semantics)
        anchor.setAttribute('tabindex', 0);
        anchor.setAttribute('role', 'button');
        anchor.setAttribute('aria-expanded', 'false');
        anchor.setAttribute(
            'aria-controls',
            getPanelForCategory(getCategory(anchor)).id
        );
    }

    /* Removes button semantics from the menu title (anchor) */
    function removeButtonSemanticsFromAnchor(anchor) {
        // Restore the href if the title was originally a link
        if (anchor.dataset.href) {
            anchor.setAttribute('href', anchor.dataset.href);
        }
        // Remove button semantics
        anchor.removeAttribute('tabindex');
        anchor.removeAttribute('role');
        anchor.removeAttribute('aria-expanded');
        anchor.removeAttribute('aria-controls');
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
