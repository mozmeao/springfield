#!/bin/bash -x

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

set -e

# Seconds to run, so a lint error still fails before the tests start.
ruff check .
ruff format --check .

# These take about half a minute, mostly Django start-up, so they run alongside the tests and
# their output is printed once the tests finish.
checks_log=$(mktemp)
(
    set -ex
    moz-l10n-lint l10n/l10n-pontoon.toml
    moz-l10n-lint l10n/l10n-vendor.toml
    python manage.py lint_ftl -q
    python manage.py migrate --noinput
    python manage.py makemigrations --check
) > "$checks_log" 2>&1 &
checks_pid=$!

# See conftest.py. CI restores the template from a cache keyed on the migrations, and builds it
# here when there is none.
if [[ -n "${TEST_DB_TEMPLATE}" && ! -f "${TEST_DB_TEMPLATE}" ]]; then
    python bin/build-test-db-template.py "${TEST_DB_TEMPLATE}"
fi

set +e
# Set PYTEST_XDIST_WORKERS=0 to run the suite in a single process when debugging.
# Keep xdist's default distribution: pytest-django runs transactional tests last because they
# flush the database, and the default keeps that order on each worker. `--dist worksteal` doesn't,
# so ordinary tests can land after a flush and lose the rows the data migrations created.
pytest lib springfield \
    -n "${PYTEST_XDIST_WORKERS:-auto}" \
    --durations=30 \
    --cov-config=.coveragerc \
    --cov-report=html \
    --cov-report=term-missing \
    --cov-report=xml:python_coverage/coverage.xml \
    --cov
tests_status=$?

pytest -r a tests/redirects
redirects_status=$?

wait "$checks_pid"
checks_status=$?
cat "$checks_log"
set -e

if [[ $tests_status -ne 0 || $redirects_status -ne 0 || $checks_status -ne 0 ]]; then
    echo "Failed: tests=$tests_status redirects=$redirects_status checks=$checks_status"
    exit 1
fi
