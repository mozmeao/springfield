/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */

'use strict';

const { defineConfig } = require('@playwright/test');
const baseConfig = require('./playwright.config');

module.exports = defineConfig({
    ...baseConfig,
    webServer: {
        command: `uv run --active python manage.py runserver 0.0.0.0:8000`,
        url: 'http://localhost:8000/healthz/',
        reuseExistingServer: !process.env.CI,
        cwd: '../../',
        env: {
            ...process.env,
            DEBUG: 'true',
            ENABLE_DJANGO_PATTERN_LIBRARY: 'true'
        }
    },
    fullyParallel: false,
    grepInvert: undefined,
    grep: /@visual-regression/,
    workers: 1,
    expect: {
        toHaveScreenshot: {
            threshold: 0.3,
            maxDiffPixelRatio: 0.02
        }
    },
    projects: [baseConfig.projects.find((p) => p.name === 'chromium')]
});
