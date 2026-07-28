/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

(function () {
    'use strict';

    // === DOM references ===

    const inlineToggle = document.getElementById('fl-docs-inline-switch');
    const indexEl = document.querySelector('.fl-docs-index');
    const sidebarEl = indexEl.querySelector('.fl-docs-index-sidebar');
    const contentEl = document.querySelector('.fl-docs-index-content');
    const savedContent = contentEl.innerHTML;
    const searchInput = document.getElementById('fl-docs-search');
    const noResultsEl = document.getElementById('fl-docs-no-results');

    let iframe = null;

    // === Inline mode ===

    /**
     * @param {string} [forcedUrl]
     * @returns {string|undefined}
     */
    function resolveInlineModeUrl(forcedUrl) {
        if (forcedUrl) return forcedUrl;

        const currentHash = window.location.hash;
        const hashLink = document.querySelector(`a[href="${currentHash}"]`);
        if (hashLink) return hashLink.dataset.url;

        const firstSidebarLink = sidebarEl.querySelector('a[data-url]');
        if (!firstSidebarLink) return;
        return firstSidebarLink.dataset.url;
    }

    /**
     * @param {HTMLIFrameElement} iframeEl
     * @returns {void}
     */
    function preventIframeScrollChaining(iframeEl) {
        try {
            const innerDoc = iframeEl.contentDocument;
            if (!innerDoc) return;
            const scrollEl =
                innerDoc.scrollingElement || innerDoc.documentElement;
            innerDoc.addEventListener(
                'wheel',
                (e) => {
                    const atTop = scrollEl.scrollTop === 0 && e.deltaY < 0;
                    const atBottom =
                        Math.ceil(scrollEl.scrollTop + scrollEl.clientHeight) >=
                            scrollEl.scrollHeight && e.deltaY > 0;
                    if (atTop || atBottom) {
                        e.preventDefault();
                    }
                },
                { passive: false }
            );
        } catch (_) {
            /* no-op */
        }
    }

    /**
     * @param {string} [forcedUrl]
     * @returns {void}
     */
    function enableInlineMode(forcedUrl) {
        const url = resolveInlineModeUrl(forcedUrl);
        if (!url) return;

        indexEl.classList.add('fl-docs-inline-mode');
        indexEl.classList.remove('max-width-wide-banner');

        iframe = document.createElement('iframe');
        iframe.className = 'fl-docs-inline-frame';
        iframe.addEventListener('load', () =>
            preventIframeScrollChaining(iframe)
        );
        contentEl.innerHTML = '';
        contentEl.appendChild(iframe);
        iframe.src = url + (url.includes('?') ? '&' : '?') + 'fl_docs_inline=1';
        if (window.matchMedia('(min-width: 1200px)').matches) {
            document.body.style.overflowY = 'hidden';
        }
        contentEl.scrollIntoView({ behavior: 'smooth' });
    }

    /** @returns {void} */
    function disableInlineMode() {
        contentEl.innerHTML = savedContent;
        iframe = null;
        document.body.style.overflowY = '';

        const hash = window.location.hash;
        reopenContentAccordionForHash(hash);

        const target = hash ? document.getElementById(hash.slice(1)) : null;
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        } else {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }

    // === Search state ===

    /** @returns {void} */
    function resetSearchFilterDisplay() {
        indexEl.querySelectorAll('.fl-docs-accordion').forEach((acc) => {
            acc.style.display = '';
        });
        indexEl
            .querySelectorAll('.fl-docs-accordion li, .fl-docs-sidebar-group')
            .forEach((el) => {
                el.style.display = '';
            });
        indexEl
            .querySelectorAll('.fl-docs-sidebar-group details')
            .forEach((d) => {
                d.open = false;
            });
        contentEl
            .querySelectorAll('article, section, details')
            .forEach((el) => {
                el.style.display = '';
            });
        contentEl
            .querySelectorAll('.fl-docs-content-accordion')
            .forEach((acc) => {
                acc.open = false;
            });
        noResultsEl.hidden = true;
    }

    /**
     * @param {string} hash
     * @returns {void}
     */
    function focusSidebarAccordionForHash(hash) {
        indexEl.querySelectorAll('.fl-docs-accordion').forEach((acc) => {
            acc.open = false;
        });
        const link = hash
            ? indexEl.querySelector(`.fl-docs-accordion a[href="${hash}"]`)
            : null;
        if (!link) return;
        link.closest('.fl-docs-accordion').open = true;
        const parentGroup = link.closest('.fl-docs-sidebar-group-details');
        if (parentGroup) parentGroup.open = true;
    }

    /**
     * @param {string} hash
     * @returns {void}
     */
    function reopenContentAccordionForHash(hash) {
        if (!hash) return;
        const contentTarget = contentEl.querySelector(
            `[id="${hash.slice(1)}"]`
        );
        if (!contentTarget) return;
        const parentAccordion = contentTarget.closest(
            '.fl-docs-content-accordion'
        );
        if (parentAccordion) parentAccordion.open = true;
    }

    /**
     * @param {string|null|undefined} destinationHash
     * @returns {void}
     */
    function applyHashSelection(destinationHash) {
        const resolvedHash =
            destinationHash !== null && destinationHash !== undefined
                ? destinationHash
                : window.location.hash;

        if (searchInput.value) {
            searchInput.value = '';
            resetSearchFilterDisplay();
            reopenContentAccordionForHash(resolvedHash);
            focusSidebarAccordionForHash(resolvedHash);
        } else if (destinationHash) {
            focusSidebarAccordionForHash(destinationHash);
        }
    }

    // === Search filters ===

    /**
     * @param {Element|null} el
     * @returns {string}
     */
    function getElementTitleText(el) {
        return el ? el.textContent.trim().toLowerCase() : '';
    }

    /**
     * @param {HTMLElement} ul
     * @param {string} query
     * @returns {boolean}
     */
    function filterSidebarList(ul, query) {
        let anyVisible = false;
        ul.querySelectorAll(':scope > li').forEach((li) => {
            if (li.classList.contains('fl-docs-sidebar-group')) {
                const summary = li.querySelector(':scope > details > summary');
                const title = getElementTitleText(summary);
                if (title.includes(query)) {
                    li.style.display = '';
                    li.querySelectorAll('li').forEach((c) => {
                        c.style.display = '';
                    });
                    anyVisible = true;
                } else {
                    const innerUl = li.querySelector(':scope > details > ul');
                    const childVisible = innerUl
                        ? filterSidebarList(innerUl, query)
                        : false;
                    li.style.display = childVisible ? '' : 'none';
                    if (childVisible) {
                        li.querySelector(
                            '.fl-docs-sidebar-group-details'
                        ).open = true;
                        anyVisible = true;
                    }
                }
            } else {
                const link = li.querySelector('a');
                const title = getElementTitleText(link);
                const visible = title.includes(query);
                li.style.display = visible ? '' : 'none';
                if (visible) anyVisible = true;
            }
        });
        return anyVisible;
    }

    /**
     * @param {HTMLElement} container
     * @param {string} query
     * @returns {boolean}
     */
    function filterContentSection(container, query) {
        let anyVisible = false;
        container
            .querySelectorAll(':scope > .fl-docs-entry')
            .forEach((article) => {
                const link = article.querySelector('h3 a, h4 a, h5 a');
                const title = getElementTitleText(link);
                const visible = title.includes(query);
                article.style.display = visible ? '' : 'none';
                if (visible) anyVisible = true;
            });
        container
            .querySelectorAll(':scope > .fl-docs-content-subsection')
            .forEach((sub) => {
                const hasVisible = filterContentSection(sub, query);
                sub.style.display = hasVisible ? '' : 'none';
                if (hasVisible) anyVisible = true;
            });
        container
            .querySelectorAll(':scope > details.fl-docs-content-accordion')
            .forEach((details) => {
                const summaryLink = details.querySelector(
                    ':scope > summary h3 a, :scope > summary h4 a, :scope > summary h5 a'
                );
                const summaryTitle = getElementTitleText(summaryLink);
                if (summaryTitle && summaryTitle.includes(query)) {
                    details.style.display = '';
                    details
                        .querySelectorAll('article, section, details')
                        .forEach((el) => {
                            el.style.display = '';
                        });
                    anyVisible = true;
                } else {
                    const body = details.querySelector(
                        '.fl-docs-content-accordion-body'
                    );
                    const hasVisible = body
                        ? filterContentSection(body, query)
                        : false;
                    details.style.display = hasVisible ? '' : 'none';
                    if (hasVisible) details.open = true;
                    if (hasVisible) anyVisible = true;
                }
            });
        return anyVisible;
    }

    // === Navigation ===

    /**
     * @param {string} hash
     * @param {string} url
     * @returns {void}
     */
    function navigateToItemInline(hash, url) {
        history.replaceState(null, '', hash);
        applyHashSelection(hash);
        inlineToggle.checked = true;
        enableInlineMode(url);
    }

    // === Event listeners ===

    inlineToggle.addEventListener('change', function () {
        indexEl.classList.toggle('fl-docs-inline-mode', this.checked);
        indexEl.classList.toggle('max-width-wide-banner', !this.checked);

        if (this.checked) {
            enableInlineMode();
        } else {
            disableInlineMode();
        }
    });

    sidebarEl.addEventListener('click', (e) => {
        const link = e.target.closest('a[data-url]');
        if (!link) return;
        if (inlineToggle.checked) {
            enableInlineMode(link.dataset.url);
        }
    });

    // Capture-phase handler for inline buttons inside accordion summaries.
    contentEl.addEventListener(
        'click',
        (e) => {
            const btn = e.target.closest('.fl-docs-inline-btn');
            if (!btn) return;
            const summary = btn.closest('summary');
            if (!summary) return;
            e.stopPropagation();
            const detailsEl = summary.closest(
                'details.fl-docs-content-accordion'
            );
            const link = summary.querySelector('a');
            if (!link || !detailsEl) return;
            navigateToItemInline('#' + detailsEl.id, link.href);
        },
        true
    );

    // Bubble-phase handler for inline buttons inside articles.
    contentEl.addEventListener('click', (e) => {
        const btn = e.target.closest('.fl-docs-inline-btn');
        if (!btn) return;
        const article = btn.closest('article');
        if (!article) return;
        const link = article.querySelector('h3 a, h4 a, h5 a');
        if (!link) return;
        navigateToItemInline('#' + article.id, link.href);
    });

    // Global delegated handler: clear search and focus sidebar on navigation.
    indexEl.addEventListener('click', (e) => {
        const target = e.target.closest('a[href], .fl-docs-inline-btn');
        if (!target) return;
        const href = target.getAttribute('href');
        if (href && href.startsWith('#')) {
            applyHashSelection(href);
        } else {
            // External link or inline-btn (already handled via navigateToItemInline).
            // applyHashSelection(null) resolves to window.location.hash, which is
            // already up-to-date when navigateToItemInline called history.replaceState.
            applyHashSelection(null);
        }
    });

    searchInput.addEventListener('input', () => {
        const query = searchInput.value.trim().toLowerCase();

        if (!query) {
            resetSearchFilterDisplay();
            const hash = window.location.hash;
            focusSidebarAccordionForHash(hash);
            reopenContentAccordionForHash(hash);
            return;
        }

        let anyVisible = false;

        indexEl.querySelectorAll('.fl-docs-accordion').forEach((accordion) => {
            const ul = accordion.querySelector(':scope > ul');
            if (!ul) return;
            const hasVisible = filterSidebarList(ul, query);
            accordion.style.display = hasVisible ? '' : 'none';
            if (hasVisible) {
                accordion.open = true;
                anyVisible = true;
            }
        });

        contentEl
            .querySelectorAll(':scope > .fl-docs-content-section')
            .forEach((section) => {
                const hasVisible = filterContentSection(section, query);
                section.style.display = hasVisible ? '' : 'none';
                if (hasVisible) anyVisible = true;
            });

        noResultsEl.hidden = anyVisible;
    });

    // === Initialisation ===

    const initHash = window.location.hash;
    focusSidebarAccordionForHash(initHash);
    reopenContentAccordionForHash(initHash);

    if (initHash) {
        const initTarget = document.getElementById(initHash.slice(1));
        if (initTarget) {
            initTarget.scrollIntoView({ behavior: 'smooth' });
        }
    }

    if (inlineToggle.checked) {
        window.setTimeout(enableInlineMode, 500);
    }
})();
