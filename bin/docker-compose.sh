#!/bin/bash -e

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

source docker/bin/set_git_env_vars.sh

# Refresh the cached apt layer weekly; see APT_REFRESH_WEEK in the Dockerfile.
export APT_REFRESH_WEEK="${APT_REFRESH_WEEK:-$(date -u +%G-%V)}"

docker compose "$@"
