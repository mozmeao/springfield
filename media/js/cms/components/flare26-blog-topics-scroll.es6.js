/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

const SCROLL_AMOUNT = 200;

function initBlogTopicsScroll(filter) {
    const list = filter.querySelector('.fl-blog-topics-list');
    const prevBtn = filter.querySelector('.fl-blog-topics-scroll-prev');
    const nextBtn = filter.querySelector('.fl-blog-topics-scroll-next');

    if (!list || !prevBtn || !nextBtn) return;

    function update() {
        const hasOverflow = list.scrollWidth > list.clientWidth;
        prevBtn.hidden = !hasOverflow;
        nextBtn.hidden = !hasOverflow;
        if (!hasOverflow) return;

        prevBtn.disabled = list.scrollLeft <= 0;
        nextBtn.disabled =
            list.scrollLeft + list.clientWidth >= list.scrollWidth - 1;
    }

    prevBtn.addEventListener('click', () => {
        list.scrollBy({ left: -SCROLL_AMOUNT, behavior: 'smooth' });
    });

    nextBtn.addEventListener('click', () => {
        list.scrollBy({ left: SCROLL_AMOUNT, behavior: 'smooth' });
    });

    list.addEventListener('scroll', update, { passive: true });

    const observer = new ResizeObserver(update);
    observer.observe(list);

    update();

    const selected = list.querySelector('.fl-blog-selected-topic');
    if (selected) {
        const listRect = list.getBoundingClientRect();
        const selectedRect = selected.getBoundingClientRect();
        if (
            selectedRect.left < listRect.left ||
            selectedRect.right > listRect.right
        ) {
            list.scrollLeft =
                selected.offsetLeft -
                list.offsetLeft -
                (list.clientWidth - selected.offsetWidth) / 2;
        }
    }
}

export default function setupBlogTopicsScroll() {
    document
        .querySelectorAll('.fl-blog-topics-filter')
        .forEach(initBlogTopicsScroll);
}
