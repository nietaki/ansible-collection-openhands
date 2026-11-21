UV ?= uv

.PHONY: install lint test molecule check

install:
	$(UV) sync --locked

lint:
	$(UV) run yamllint .
	$(UV) run ansible-lint

# The contract tests use only the Python standard library for portability.
test:
	$(UV) run python -m unittest discover -s tests -p 'test_*.py'

molecule:
	$(UV) run molecule test -s default

check: lint test molecule
