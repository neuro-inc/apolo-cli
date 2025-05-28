SHELL := /bin/bash

PYTEST_ARGS=

PYTEST_XDIST_NUM_THREADS ?= auto
COLOR ?= auto

.PHONY: help
.SILENT: help
help:
	@# generate help message by parsing current Makefile
	@# idea: https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
	@grep -hE '^[a-zA-Z_-]+:[^#]*?### .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: setup init
setup init: _init-cli-help ### Setup the project
	poetry install --with dev,ci,doc
	rm -rf .mypy_cache
	pre-commit install

_init-cli-help:
	cp -n CLI.in.md CLI.md

.PHONY: update-deps
update-deps: ### Update dependencies
	poetry update
	touch .update-deps

.update-deps: pyproject.toml poetry.lock
	poetry install --with dev,ci,doc
	touch .update-deps

.PHONY: .e2e
.e2e:
	COLUMNS=160 LINES=75 poetry run pytest \
		-n ${PYTEST_XDIST_NUM_THREADS} \
		--dist loadgroup \
		-m "e2e" \
		--cov=apolo-cli --cov=apolo-sdk \
		--cov-report term-missing:skip-covered \
		--cov-report xml:coverage.xml \
		--verbose \
		--color=$(COLOR) \
		--durations 10 \
		$(PYTEST_ARGS) \
		apolo-cli/tests

.PHONY: e2e
e2e: .update-deps .e2e ### Run end-to-end tests

.PHONY: .test
.test-sdk:
	poetry run pytest \
		-m "not e2e" \
		--cov=apolo-sdk \
		--cov-report term-missing:skip-covered \
		--cov-report xml:coverage.xml \
		--color=$(COLOR) \
		$(PYTEST_ARGS) \
		apolo-sdk/tests

.PHONY: .test-sdk
test-sdk: .update-deps .test-sdk ### Run unit tests

.PHONY: .test
.test-cli:
	poetry run pytest \
		-m "not e2e" \
		--cov=apolo-cli \
		--cov-report term-missing:skip-covered \
		--cov-report xml:coverage.xml \
		--color=$(COLOR) \
		$(PYTEST_ARGS) \
		apolo-cli/tests

.PHONY: .test-cli
test-cli: .update-deps .test-cli ### Run unit tests

.PHONY: test-all
test-all: .update-deps ### Run all tests
	poetry run pytest \
		--cov=apolo-sdk/apolo_sdk --cov=apolo-cli/apolo_cli \
		--cov-report term-missing:skip-covered \
		--cov-report xml:coverage.xml \
		--color=$(COLOR)


.PHONY: format fmt
format fmt: ### Reformat source files and run linters
ifdef CI_LINT_RUN
	poetry run pre-commit run --all-files --show-diff-on-failure
else
	poetry run pre-commit run --all-files
endif


.PHONY: lint
lint: fmt ### Reformat files, run linters and mypy checks
	poetry run mypy apolo-sdk --show-error-codes
	poetry run mypy apolo-cli --show-error-codes

.PHONY: publish-lint
publish-lint: ### Check for publishing safety
	poetry check -C apolo-sdk
	poetry check -C apolo-cli


.PHONY: clean
clean: ### Cleanup temporary files
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '__pycache__' -exec rm -rf {} +
	rm -rf CLI.md
	rm -rf .mypy_cache

.PHONY: docs
docs: ### Generate CLI docs
	poetry run python build-tools/cli-help-generator.py CLI.in.md CLI.md
	markdown-toc -t github -h 6 CLI.md
	poetry run python build-tools/site-help-generator.py


.PHONY: api-doc
api-doc: ### Generate API docs
	make -C apolo-sdk/docs html SPHINXOPTS="-W -E"
	@echo "open file://`pwd`/apolo-sdk/docs/_build/html/index.html"

.PHONY: api-doc-spelling
api-doc-spelling: ### Spell check API docs
	make -C apolo-sdk/docs spelling SPHINXOPTS="-W -E"
	@echo "open file://`pwd`/apolo-sdk/docs/_build/html/index.html"

.PHONY: build
build: ### Build distribution packages
	rm -rf dist/
	poetry build -C apolo-sdk
	poetry build -C apolo-cli

.PHONY: publish
publish: build publish-lint ### Publish to PyPI
	poetry publish -C apolo-sdk
	poetry publish -C apolo-cli

.PHONY: publish-test
publish-test: build publish-lint ### Publish to Test PyPI
	poetry publish -C apolo-sdk -r testpypi
	poetry publish -C apolo-cli -r testpypi
