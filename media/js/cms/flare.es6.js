/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

import setupAnimations from './components/flare-animations.es6';
import setupBlogTopicsScroll from './components/flare-blog-topics-scroll.es6';
import setupCarousels from './components/flare-carousel.es6';
import setupCopyToClipboardButtons from './components/flare-copy-to-clipboard.es6';
import setupDialogs, { initDialogs } from './components/flare-dialogs.es6';
import setupDownloadDropdown from './components/flare-download-dropdown.es6';
import setupFirefoxVersionConditionalDisplay from './components/flare-firefox-version.es6';
import setupLastVisibleBanner from './components/flare-last-visible-banner.es6';
import setupNewsletter from './components/flare-newsletter.es6';
import setupNotificationClose from './components/flare-notification-close.es6';
import setupQRCodeSnippet from './components/flare-qr-code-snippet.es6';
import setupScrollingCardGrid from './components/flare-scrolling-card-grid.es6';
import { setupSetAsDefault } from './components/flare-set-as-default.es6';
import setupSlidingCarousels from './components/flare-sliding-carousel.es6';
import setupRoadmapFilter from './components/flare-roadmap-filter.es6';
import setupTopicListSidebar from './components/flare-topic-list-sidebar.es6';
import setupTypewriter, { typewriter } from './components/flare-typewriter.es6';
import setupVideo from './components/flare-video.es6';

// Create namespace
if (typeof window.cms === 'undefined') {
    window.cms = {};
}

window.cms.flare = { typewriter, initDialogs };

function setupComponents() {
    setupBlogTopicsScroll();
    setupNewsletter();
    setupNotificationClose();
    setupVideo();
    setupAnimations();
    setupDownloadDropdown();
    setupQRCodeSnippet();
    setupRoadmapFilter();
    setupTopicListSidebar();
    setupTypewriter();
    setupDialogs();
    setupCarousels();
    setupScrollingCardGrid();
    setupCopyToClipboardButtons();
    setupFirefoxVersionConditionalDisplay();
    setupSlidingCarousels();
    setupSetAsDefault();
    setupLastVisibleBanner();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupComponents);
} else {
    setupComponents();
}
