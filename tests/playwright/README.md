# Playwright Tests

End-to-end, accessibility, and visual regression tests for Springfield, built with [Playwright](https://playwright.dev/).

## Requirements

- Node.js
- A running Springfield instance (defaults to `http://localhost:8000`)

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

```sh
# Run comparisons against existing baselines
npm run visual-regression-tests

# Open the interactive Playwright UI
npm run visual-regression-tests:ui

# Regenerate baseline screenshots
npm run update-screenshots
```

The visual regression config (`playwright.visual-regression.config.js`) extends the base config but disables parallelism and restricts runs to Chromium.
