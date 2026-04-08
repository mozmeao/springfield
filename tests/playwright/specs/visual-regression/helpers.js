/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { expect } = require('@playwright/test');

async function expectComponentScreenshot(page, testId, snapshotName) {
    await expect(page.locator(`[data-testid="${testId}"]`)).toHaveScreenshot(
        `${snapshotName ?? testId}.png`,
        { animations: 'disabled' }
    );
}

module.exports = {
    patternLibraryURL:
        '/pattern-library/render-pattern/pattern-library/components',
    expectComponentScreenshot
};
