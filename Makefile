UV ?= uv

.PHONY: install lint lint-yaml test molecule check

install:
	$(UV) sync --locked

lint: lint-yaml
	$(UV) run ansible-lint

lint-yaml:
	git ls-files -z -- '*.yml' '*.yaml' | xargs -0 $(UV) run yamllint

# The contract tests use only the Python standard library for portability.
test:
	$(UV) run python -m unittest discover -s tests -p 'test_*.py'

molecule:
	$(UV) run molecule test -s default

check: lint test molecule
