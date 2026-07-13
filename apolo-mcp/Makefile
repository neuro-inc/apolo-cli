SHELL := /bin/bash

PYTEST_ARGS=

.PHONY: help
.SILENT: help
help:
	@grep -hE '^[a-zA-Z_-]+:[^#]*?### .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: setup
setup: ### Install dev dependencies and pre-commit hooks
	uv sync --all-groups
	uv run pre-commit install

.PHONY: format fmt
format fmt: ### Reformat source files
ifdef CI_LINT_RUN
	uv run pre-commit run --all-files --show-diff-on-failure
else
	uv run pre-commit run --all-files
endif

.PHONY: lint
lint: format ### Reformat + mypy
	uv run mypy src/ --show-error-codes

.PHONY: test
test: ### Run unit tests
	uv run pytest $(PYTEST_ARGS) tests/

.PHONY: build
build: ### Build sdist and wheel
	uv build

.PHONY: publish
publish: ### Publish to PyPI (set UV_PUBLISH_TOKEN env var)
	uv publish

.PHONY: run
run: ### Run the MCP server (stdio transport)
	uv run python -m apolo_mcp

.PHONY: clean
clean: ### Remove build artifacts
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '__pycache__' -exec rm -rf {} +
	rm -rf .mypy_cache dist build
