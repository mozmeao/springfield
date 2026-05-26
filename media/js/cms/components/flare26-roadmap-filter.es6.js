/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const PARAM = 'tags';

function getActiveFilters() {
    const params = new URLSearchParams(window.location.search);
    const value = params.get(PARAM);
    return value ? new Set(value.split(',').filter(Boolean)) : new Set();
}

function setUrlParams(activeFilters) {
    const url = new URL(window.location.href);
    if (activeFilters.size > 0) {
        url.searchParams.set(PARAM, [...activeFilters].join(','));
    } else {
        url.searchParams.delete(PARAM);
    }
    history.replaceState(null, '', url);
}

function applyFilter(activeFilters) {
    const sections = document.querySelectorAll('.fl-roadmap-list-section');

    sections.forEach((section) => {
        const items = section.querySelectorAll('.fl-roadmap-item');
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

function syncButtonState(filterButtons, activeFilters) {
    filterButtons.forEach((button) => {
        const isActive = activeFilters.has(button.dataset.filter);

        const tag = button.querySelector('.fl-tag');
        if (tag) {
            tag.classList.toggle('is-selected', isActive);
        }
        button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });
}

function initRoadmapFilter() {
    const filterButtons = document.querySelectorAll(
        '.fl-roadmap-filter-button'
    );
    if (!filterButtons.length) return;

    const activeFilters = getActiveFilters();

    if (activeFilters.size > 0) {
        syncButtonState(filterButtons, activeFilters);
        applyFilter(activeFilters);
    }

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
}

export default function setupRoadmapFilter() {
    initRoadmapFilter();
}
