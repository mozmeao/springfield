/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

/** @type {string} - The URL query parameter name used to store selected filter tags */
const PARAM = 'tags';

/**
 * Reads the current URL query string and returns the active filter tags as a Set.
 * @returns {Set<string>} Set of active tag filters from the URL
 */
function getActiveFilters() {
    /** @type {URLSearchParams} */
    const params = new URLSearchParams(window.location.search);
    const value = params.get(PARAM);
    return value ? new Set(value.split(',').filter(Boolean)) : new Set();
}

/**
 * Updates the browser URL with the given set of active filters.
 * Uses replaceState so it doesn't add a history entry.
 * @param {Set<string>} activeFilters - The set of currently selected filter tags
 */
function setUrlParams(activeFilters) {
    const url = new URL(window.location.href);
    if (activeFilters.size > 0) {
        url.searchParams.set(PARAM, [...activeFilters].join(','));
    } else {
        url.searchParams.delete(PARAM);
    }
    history.replaceState(null, '', url);
}

/**
 * Shows/hides roadmap items and sections based on the active filters.
 * Items matching any active filter are shown; unmatched items are hidden.
 * Sections with no visible items are hidden entirely.
 * @param {Set<string>} activeFilters - The set of currently selected filter tags
 */
function applyFilter(activeFilters) {
    const sections = document.querySelectorAll('.fl-roadmap-list-section');

    sections.forEach((section) => {
        const items = section.querySelectorAll('.fl-roadmap-item');
        /** @type {number} - Count of visible items in this section */
        let visibleCount = 0;

        items.forEach((item) => {
            const tags = item.dataset.tags ? item.dataset.tags.split(',') : [];
            const visible =
                activeFilters.size === 0 ||
                tags.some((tag) => activeFilters.has(tag));

            item.classList.toggle('hidden', !visible);

            item.querySelectorAll('span[data-tag]').forEach((tagEl) => {
                const tag = tagEl.querySelector('.fl-tag');
                if (tag) {
                    tag.classList.toggle(
                        'is-selected',
                        visible && activeFilters.has(tagEl.dataset.tag)
                    );
                }
            });

            if (visible) {
                visibleCount++;
            }
        });

        section.classList.toggle(
            'hidden',
            activeFilters.size > 0 && visibleCount === 0
        );
    });
}

/**
 * Updates the visual state (aria-pressed, selected class) of filter buttons
 * to reflect the current set of active filters.
 * @param {NodeList} filterButtons - The filter toggle buttons in the DOM
 * @param {Set<string>} activeFilters - The set of currently selected filter tags
 */
function syncButtonState(filterButtons, activeFilters) {
    filterButtons.forEach((button) => {
        const isActive = activeFilters.has(button.dataset.filter);

        const tag = button.querySelector('.fl-tag');
        if (tag) {
            tag.classList.toggle('is-selected', isActive);
        }
        button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });

    const clearAllButton = document.querySelector(
        '.fl-roadmap-filter-button-clear-all'
    );

    if (clearAllButton && activeFilters.size) {
        clearAllButton.disabled = false;
        clearAllButton.querySelector('.fl-tag').classList.add('is-selected');
    } else {
        clearAllButton.disabled = true;
        clearAllButton.querySelector('.fl-tag').classList.remove('is-selected');
    }
}

/**
 * Initializes the roadmap filter component: applies any filters from the URL
 * and attaches click handlers to the filter buttons.
 */
function initRoadmapFilter() {
    const filterButtons = document.querySelectorAll(
        '.fl-roadmap-filter-button:not(.fl-roadmap-filter-button-clear-all)'
    );
    if (!filterButtons.length) return;

    /** @type {Set<string>} */
    const activeFilters = getActiveFilters();

    syncButtonState(filterButtons, activeFilters);
    applyFilter(activeFilters);

    filterButtons.forEach((button) => {
        button.addEventListener('click', () => {
            const filter = button.dataset.filter;

            if (activeFilters.has(filter)) {
                activeFilters.delete(filter);
            } else {
                activeFilters.add(filter);
            }

            syncButtonState(filterButtons, activeFilters);
            applyFilter(activeFilters);
            setUrlParams(activeFilters);
        });
    });

    const clearAllButton = document.querySelector(
        '.fl-roadmap-filter-button-clear-all'
    );
    if (clearAllButton) {
        clearAllButton.addEventListener('click', () => {
            activeFilters.clear();
            syncButtonState(filterButtons, activeFilters);
            applyFilter(activeFilters);
            setUrlParams(activeFilters);
        });
    }
}

/**
 * Entry point for the roadmap filter module.
 * Called from the template when the page is ready.
 */
export default function setupRoadmapFilter() {
    initRoadmapFilter();
}
