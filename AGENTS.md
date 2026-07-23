# Repository Guidelines

## Project Structure & Module Organization

Springfield is a Django monolith: core apps, views, and templates live in `springfield/`. Shared helpers sit in `lib/`, while automated checks and integration flows reside in `tests/`. Front-end source (Sass, JS, icons) lives under `media/`; webpack entry points are in `assets/`, and collected output is in `static/`. Infrastructure and localization assets are under `docker/`, `docs/`, and `l10n/`—update them when deployment or translation changes land.

## Build, Test, and Development Commands

Review the full setup notes in the platform docs (`https://mozmeao.github.io/platform-docs/`) before first use - cache these if you can.

Copy `.env-dist` to `.env`, then run `make preflight` to install Python deps and pull the latest content bundle.
`make run` launches the Docker Compose stack (web plus asset builders); most `make` commands execute inside containers.

For local-only loops, `npm start` serves Django and webpack with live rebuilds, and `pytest springfield` runs backend tests without Docker.

Use `make test` for the containerized pytest + Jasmine suite, `uv run pytest springfield` for the quick "bare metal" Django tests and `npm run lint` to mirror the CI lint container.

## Coding Style & Naming Conventions

Python targets 3.13 with Ruff enforcing ≤150-character lines and import ordering of Django → third-party → first-party.

Prefer snake_case for functions, `CamelCase` for Django classes, and descriptive template names under `springfield/<app>/templates/`.
JavaScript follows the ESLint + Prettier ruleset with `const`/`let`; run `npm run format` before committing.

Sass in `media/css/` keeps the existing block–element naming pattern.

If you add an inline import (i.e. an import anywhere inside a function or class) to Python code, it MUST be accompanied by a comment explaining why it is an inline import.

## Testing Guidelines

Pytest expects files named `test_<feature>.py` beside code or in `tests/unit/` or `tests/functional/`.
Use markers such as `cdn`, `smoke`, or `skip_if_firefox` to scope runs (e.g., `pytest -m "not cdn"`). `npm run jasmine` rebuilds assets via `webpack.test.config.js` and runs front-end unit coverage. `make test` is the containerized umbrella; browser flows in `tests/playwright/` require QA coordination before extending.

## Workflow guidelines

When working on a feature or fix, work on a dedicated branch whose name is prefixed with the relevant issue number (or nothing) and then is a kebab-cased short term for the branch. Ask for the issue ID and a short summary, turning "12345" and "Amend CSS shadows for nav" to "12345--amend-css-shadows-for-nav". Use the Issue ID to generate a URL for it (<https://github.com/mozmeao/springfield/issues/ISSUE_ID>) and see if the descroption helps you work on the task. Always offer to run the tests after the work appears to be complete.

## Commit & Pull Request Guidelines

Keep commit titles short, imperative, and linked to issues when available (e.g., `Tighten hero metrics (#16595)`). Focus diffs and note migrations, toggles, or telemetry changes. Flag rollout considerations when touching configuration under `docker/`, `**/migrations/` or monitoring.

### Writing PR descriptions

Fill in every section of `.github/PULL_REQUEST_TEMPLATE.md` — never leave a heading blank. The goal is to *direct the reviewer's attention*, not to restate the diff. Before writing, inspect what actually changed (`git diff --stat main...`, plus a scan for migrations, fixtures, config, and deletions) so the description matches reality. A good description lets a reviewer know where to look hard and where to skim.

**One-line summary.** Keep it concise and lead with the main intention or change. One clear sentence is plenty — e.g. `Refactor card blocks into a single unified CardBlock.` A reviewer should grasp the point of the PR from this line alone.

**Significant changes and points to review.** This is the core of the description. Don't dump a file list — group the diff into a handful of labelled topics and explain each so the reviewer can see the key elements that carry the most significant changes:
- Give each item a short label for the area of change. Anchor it to whatever makes the change easiest to find: a file or path, a model or component name, or — when no single code entity fits — the area or part of the system affected (e.g. "the migration", "the pattern library", "CSS for the card variants").
- Say *what* changed and *why* — what it replaces, what it enables, what behaviour is now different. Intent over mechanics.
- Order items most-significant first. Fold low-risk, mechanical fallout (updated fixtures, ported static pages, renamed CSS) into their own short items so the reviewer knows the blast radius without wading through it.
- **Explicitly flag the single riskiest / most important thing to review** and say so in plain words — e.g. append "this is the most critical part to review". Data migrations, schema changes, anything hard to reverse or easy to get subtly wrong belongs here.
- Be honest about risk and about anything you're unsure of; the point of a review is to catch what you couldn't.

**Issue / Bugzilla link.** Paste the full tracker URL (Jira/Bugzilla/GitHub issue). Not just an ID.

**Testing.** Give concrete, reproducible steps a reviewer can follow to verify the change, in order. Include data setup where relevant (fresh db, run migrations, load fixtures) and state what to check — which variants, which pages, what should look or behave the same. Prefer a short numbered/bulleted checklist over prose. Note `make test`, screenshots, or pattern-library/Flare-docs checks when they apply.

## Security & Configuration Tips

* Keep secrets out of version control.
* Use a 12-Factor App pattern and an .env file.
* Where necessary (eg JSON credential files) store machine-specific credentials in `local-credentials/`.
* Install the local git hooks via `make install-custom-git-hooks`.
* If a changeset includes a GitHub Action or Workflow, use [Zizmor](https://zizmor.sh/) to check it for security issues before considering the work complete.

## Wagtail CMS

* When planning Wagtail work, remember that <https://docs.wagtail.org/en/7.3/llms.txt> and the full version at <https://docs.wagtail.org/en/7.3/llms-full.txt> contain LLM-appropriate documentation.
* If the version of Wagtail (not counting patch releases) in requirements/prod.in doesn't match the version in the LLM-appropriate URLs mentioned, please update this AGENTS.md then load the new info

## LLM assistance

* When committing code, do not list the LLM as a co-author - it is a tool, not a developer. All code committed is the responsibility of the human developer using the LLM. This is in line with <https://firefox-source-docs.mozilla.org/contributing/ai-coding.html>
