# Playwright Tests

End-to-end, accessibility, and visual regression tests for Springfield, built with [Playwright](https://playwright.dev/).

## Requirements

- Node.js
- A running Springfield instance (defaults to `http://localhost:8000`)
- Docker (for visual regression tests)

## Setup

Install dependencies and Playwright browsers:

```sh
npm install
npm run install-deps
```

The configs read environment variables from the root `.env` file (see `.env-dist`). To point tests at a different host, set `PLAYWRIGHT_BASE_URL`:

```sh
PLAYWRIGHT_BASE_URL=https://www.firefox.com npm run integration-tests
```

## Test suites

### Integration tests

Functional tests covering Firefox product pages, consent banner, newsletter embeds, Google Analytics, and more. Runs across Chromium, Firefox, and WebKit.

```sh
npm run integration-tests
```

Specs live in `specs/` (all files except those tagged `@a11y` or `@visual-regression`).

### Accessibility tests

Uses [axe-core](https://github.com/dequelabs/axe-core) to scan pages for WCAG violations at both desktop (1280×720) and mobile (360×780) viewports. Runs on Chromium only. HTML reports are written to `test-results-a11y/`.

```sh
npm run a11y-tests
```

Pages scanned are defined in [specs/a11y/includes/urls.js](specs/a11y/includes/urls.js).

### Visual regression tests

Screenshot comparison tests tagged `@visual-regression`. Uses a single Chromium worker with a pixel-diff threshold to avoid flaky results. Baseline screenshots are committed to the repo.

These tests run inside Docker using the official Playwright image to ensure consistent screenshots across machines. Your local Springfield instance must be running before executing them.

```sh
# Run comparisons against existing baselines
npm run visual-regression-tests

# Open the interactive Playwright UI (available at http://localhost:8085)
npm run visual-regression-tests:ui

# Regenerate baseline screenshots
npm run update-screenshots
```

Screenshots are written directly to the `specs/visual-regression/` snapshot directories on your host machine via a volume mount.

By default the tests reach your local dev server at `http://host.docker.internal:8000`. If you're running Springfield inside Docker instead, set in the root `.env`:

```sh
PLAYWRIGHT_BASE_URL=http://assets:8000
```

To run without Docker, use the `local:` variants:

```sh
npm run local:visual-regression-tests
npm run local:visual-regression-tests:ui
npm run local:update-screenshots
```

The visual regression config (`playwright.visual-regression.config.js`) extends the base config but disables parallelism and restricts runs to Chromium.

### Live page comparison tests

Takes full-page screenshots of the same pages on two different hosts and fails if any pair differs. Useful for verifying a local or staging environment matches the live site before a deploy.

The tests run on Chromium only. Both screenshots are saved to `test-results/compare-live/` for inspection, and a pixel diff image is generated there on failure. No baseline files are committed to the repo — the live site screenshot is always captured fresh as the reference.

```sh
# Compare localhost:8000 against www.firefox.com (defaults)
npm run compare-live-pages

# Compare a staging host against the live site
HOST_A=https://staging.example.com npm run compare-live-pages

# Open the interactive Playwright UI
npm run compare-live-pages:ui
```

Override either host via environment variables:

| Variable | Default |
|---|---|
| `HOST_A` | `http://localhost:8000` |
| `HOST_B` | `https://www.firefox.com` |

#### Authentication

If the target host sits behind a login page (e.g. Google SSO), log in once to save a session:

```sh
npm run compare-live-pages:login
```

This opens a browser window. Navigate to the login page, complete sign-in, then close the browser. The session cookies are saved to `.auth/compare-live-auth.json` (gitignored) and loaded automatically on subsequent runs. They persist until you log in again.
