# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# intended to be sourced into other scripts to set the git environment varaibles
# GIT_COMMIT, GIT_COMMIT_SHORT, GIT_TAG, GIT_TAG_DATE_BASED, GIT_BRANCH, and BRANCH_NAME.

if [[ -z "$GIT_COMMIT" ]]; then
    export GIT_COMMIT=$(git rev-parse HEAD)
fi
export GIT_COMMIT_SHORT="${GIT_COMMIT:0:9}"
if [[ -z "$GIT_TAG" ]]; then
    export GIT_TAG=$(git describe --tags --exact-match $GIT_COMMIT 2> /dev/null)
fi
if [[ "$GIT_TAG" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}(\.[0-9])?$ ]]; then
    export GIT_TAG_DATE_BASED=true
fi
if [[ -z "$GIT_BRANCH" ]]; then
    if [[ -n "$CI_COMMIT_REF_NAME" ]]; then
        export GIT_BRANCH="$CI_COMMIT_REF_NAME"
    else
        export GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    fi
    export BRANCH_NAME="$GIT_BRANCH"
fi
export BRANCH_NAME_SAFE="${BRANCH_NAME/\//-}"
export BRANCH_AND_COMMIT="${BRANCH_NAME_SAFE}-${GIT_COMMIT}"
# Docker Hub Stuff
export DEPLOYMENT_DOCKER_REPO="mozmeao/springfield"
export DEPLOYMENT_DOCKER_IMAGE="${DEPLOYMENT_DOCKER_REPO}:${GIT_COMMIT}"
