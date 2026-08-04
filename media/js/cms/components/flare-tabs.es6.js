/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

class TabsAutomatic {
    constructor(groupNode) {
        this.tablistNode = groupNode;

        this.firstTab = null;
        this.lastTab = null;

        this.tabs = Array.from(this.tablistNode.querySelectorAll('[role=tab]'));
        this.tabpanels = [];

        for (let i = 0; i < this.tabs.length; i += 1) {
            const tab = this.tabs[i];
            const tabpanel = document.getElementById(
                tab.getAttribute('aria-controls')
            );

            tab.setAttribute('aria-selected', 'false');
            this.tabpanels.push(tabpanel);

            tab.addEventListener('keydown', this.onKeydown.bind(this));
            tab.addEventListener('click', this.onClick.bind(this));

            if (!this.firstTab) {
                this.firstTab = tab;
            }
            this.lastTab = tab;
        }

        this.setSelectedTab(this.firstTab, false);
    }

    setSelectedTab(currentTab, setFocus) {
        if (typeof setFocus !== 'boolean') {
            setFocus = true;
        }
        for (let i = 0; i < this.tabs.length; i += 1) {
            const tab = this.tabs[i];
            const tabpanel = this.tabpanels[i];
            const isCurrent = currentTab === tab;

            tab.setAttribute('aria-selected', isCurrent ? 'true' : 'false');
            // Tabindex: only the current tab is in the keyboard focus
            // order, the rest are reachable via arrow/Home/End keys.
            tab.setAttribute('tabindex', isCurrent ? '0' : '-1');
            if (tabpanel) {
                tabpanel.classList.toggle('is-hidden', !isCurrent);
            }
            if (isCurrent && setFocus) {
                tab.focus();
            }
        }
    }

    setSelectedToPreviousTab(currentTab) {
        if (currentTab === this.firstTab) {
            this.setSelectedTab(this.lastTab);
        } else {
            const index = this.tabs.indexOf(currentTab);
            this.setSelectedTab(this.tabs[index - 1]);
        }
    }

    setSelectedToNextTab(currentTab) {
        if (currentTab === this.lastTab) {
            this.setSelectedTab(this.firstTab);
        } else {
            const index = this.tabs.indexOf(currentTab);
            this.setSelectedTab(this.tabs[index + 1]);
        }
    }

    /* EVENT HANDLERS */

    onKeydown(event) {
        const tgt = event.currentTarget;
        let flag = false;

        switch (event.key) {
            case 'ArrowLeft':
                this.setSelectedToPreviousTab(tgt);
                flag = true;
                break;

            case 'ArrowRight':
                this.setSelectedToNextTab(tgt);
                flag = true;
                break;

            case 'Home':
                this.setSelectedTab(this.firstTab);
                flag = true;
                break;

            case 'End':
                this.setSelectedTab(this.lastTab);
                flag = true;
                break;

            default:
                break;
        }

        if (flag) {
            event.stopPropagation();
            event.preventDefault();
        }
    }

    onClick(event) {
        this.setSelectedTab(event.currentTarget);
    }
}

export default function setupTabs() {
    const tablists = document.querySelectorAll('.fl-tabs-nav[role="tablist"]');
    tablists.forEach(function (tablist) {
        new TabsAutomatic(tablist);
    });
}
