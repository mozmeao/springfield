DC_CI = "bin/docker-compose.sh"
DC = $(shell which docker) compose
DOCKER = $(shell which docker)
TEST_DOMAIN = www.firefox.com

# Check if 'uv' exists and set the command accordingly
ifneq (, $(shell which uv 2>/dev/null))
	pip = uv pip
else
	pip = pip
endif

all: help

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  build                          - build docker images for dev"
	@echo "  run                            - 'docker compose up' the entire system for dev"
	@echo "  stop                           - stop all docker containers"
	@echo "  kill                           - kill all docker containers (more forceful than stop)"
	@echo "  pull                           - pull the latest production images from Docker Hub"
	@echo "  run-shell                      - open a bash shell in a fresh container"
	@echo "  shell                          - open a bash shell in the running app"
	@echo "  djshell                        - start the Django Python shell in the running app"
	@echo "  fresh-data                     - pull the latest database and update all external data"
	@echo "  clean                          - remove all build, test, coverage and Python artifacts"
	@echo "  rebuild                        - force a rebuild of all of the docker images"
	@echo "  lint                           - check style with Ruff, ESlint, Stylelint, and Prettier"
	@echo "  format                         - format front-end code using Stylelint and Prettier"
	@echo "  test                           - run tests against local files"
	@echo "  test-image                     - run tests against files in docker image"
	@echo "  test-cdn                       - run CDN tests against TEST_DOMAIN"
	@echo "  docs                           - generate Sphinx HTML documentation with server and live reload using Docker"
	@echo "  livedocs                       - generate Sphinx HTML documentation with server and live reload"
	@echo "  build-docs                     - generate Sphinx HTML documentation using Docker"
	@echo "  build-ci                       - build docker images for use in our CI pipeline"
	@echo "  test-ci                        - run tests against files in docker image built by CI"
	@echo "  compile-requirements           - update Python requirements files using pip-compile"
	@echo "  check-requirements             - get a report on stale/old Python dependencies in use"
	@echo "  install-local-python-deps      - install Python dependencies for local development"
	@echo "  install-custom-git-hooks       - install custom git hooks"
	@echo "  uninstall-custom-git-hooks     - uninstall custom git hooks"
	@echo "  clean-local-deps               - remove all local installed Python dependencies"
	@echo "  preflight                      - refresh installed dependencies and fetch latest DB ahead of local dev"
	@echo "  preflight -- --retain-DB	- refresh installed dependencies WITHOUT fetching latest DB"
	@echo "  run-local-task-queue           - run rqworker on your local machine. Requires redis to be running"

.env:
	@if [ ! -f .env ]; then \
		echo "Copying .env-dist to .env..."; \
		cp .env-dist .env; \
	fi

.docker-build:
	${MAKE} build

.docker-build-pull:
	${MAKE} pull

build: .docker-build-pull
	${DC} build --pull app assets
	touch .docker-build

build-prod: .docker-build-pull
	${DC} build --pull release

pull: .env
	-GIT_COMMIT= ${DC} pull release app assets builder app-base
	touch .docker-build-pull

rebuild: clean build

run: .docker-build-pull
	${DC} up assets app

run-prod: .docker-build-pull
	${DC} up release-local

stop:
	${DC} stop

kill:
	${DC} kill

fresh-data:
	${DC} exec app bin/sync-all.sh

run-shell:
	${DC} run --rm app bash

shell:
	${DC} exec app bash

djshell:
	${DC} exec app python manage.py shell_plus

clean:
#	python related things
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +
#	test related things
	-rm -f .coverage
#	docs files
	-rm -rf docs/_build/
#	static files
	-rm -rf static_build/
#	state files
	-rm -f .docker-build*
# clean untracked files & directories
	git clean -d -f

lint: .docker-build-pull
	${DC} run test ruff
	${DC} run assets npm run lint

format: .docker-build-pull
	${DC} run assets npm run format
	${DC} run app ruff format .

test: .docker-build-pull
	${DC} run --rm test

test-cdn: .docker-build-pull test_infra/fixtures/tls.json
	${DC} run test pytest --base-url https://${TEST_DOMAIN} -m cdn

test-image: .docker-build
	${DC} run test-image

docs: .docker-build-pull
	${DC} up docs

build-docs: .docker-build-pull
	${DC} run app make -C docs/ clean html

livedocs:
	${MAKE} -C docs/ clean livehtml

test_infra/fixtures/tls.json:
	${DOCKER} run -it --rm jumanjiman/ssllabs-scan:latest --quiet https://${TEST_DOMAIN}/en-US/ > "test_infra/fixtures/tls.json"

###############
# For use in CI
###############
.docker-build-ci:
	${MAKE} build-ci

build-ci: .docker-build-pull
	${DC_CI} build --pull release
#	tag intermediate images using cache
	${DC_CI} build app builder assets app-base
	touch .docker-build-ci

test-ci: .docker-build-ci
	${DC_CI} run test-image

#########################
# Requirements management
#########################

compile-requirements: .docker-build-pull
	${DC} run --rm compile-requirements

check-requirements: .docker-build-pull
	${DC} run --rm app ./bin/check-pinned-requirements.py

######################################################
# For use in local-machine development (not in Docker)
######################################################

# Trick to avoid treating flags (eg --retain-db) as a make target
%:
	@:

preflight:
	${MAKE} install-local-python-deps
	@npm install
	@$(if $(findstring --retain-db,$(MAKECMDGOALS)),bin/sync-all.sh --retain-db,bin/sync-all.sh)
	@python manage.py bootstrap_local_admin

install-local-python-deps:
	# Dev requirements are a superset of prod requirements, but we install
	# them in the same separate steps that we use for our Docker-based build,
	# so that it mirrors Production and Dev image building
	$(pip) install -r requirements/prod.txt
	$(pip) install -r requirements/dev.txt

run-local-task-queue:
	# We temporarily source the .env for the command's duration only
	(source ".env" && \
		[ -n "$$REDIS_URL" ] || { echo "REDIS_URL env var is not set"; exit 1; } && \
		./bin/run-worker.sh)


clean-local-deps:
	$(pip) uninstall mdx_outline -y && $(pip) freeze | xargs $(pip) uninstall -y

# Done explicitly to avoid surprises
install-custom-git-hooks:
	cp bin/custom-git-hooks/post-merge .git/hooks/post-merge
	chmod u+x .git/hooks/post-merge

# Done explicitly to avoid surprises
uninstall-custom-git-hooks:
	rm .git/hooks/post-merge

.PHONY: all clean build pull docs livedocs build-docs lint run stop kill run-shell shell test test-image rebuild build-ci test-ci fresh-data djshell run-prod build-prod test-cdn compile-requirements check-requirements install-local-python-deps preflight clean-local-deps install-custom-git-hooks uninstall-custom-git-hooks run-local-task-queue
