UV ?= uv
COLLECTION_VERSION := $(shell awk '$$1 == "version:" { gsub(/"/, "", $$2); print $$2 }' galaxy.yml)
COLLECTION_BUILD_DIR := .ansible/collection-build
COLLECTION_INSTALL_DIR := .ansible/collections
COLLECTION_ARTIFACT := $(COLLECTION_BUILD_DIR)/nietaki-openhands-$(COLLECTION_VERSION).tar.gz
export ANSIBLE_COLLECTIONS_PATH := $(CURDIR)/$(COLLECTION_INSTALL_DIR)

.PHONY: install collection-install lint lint-yaml test molecule molecule-persistence \
	molecule-persistence-version-only molecule-persistence-verified check \
	release-patch release-minor release-major

install:
	$(UV) sync --locked

collection-install:
	mkdir -p $(COLLECTION_BUILD_DIR) $(COLLECTION_INSTALL_DIR)
	$(UV) run ansible-galaxy collection build --force --output-path $(COLLECTION_BUILD_DIR)
	$(UV) run ansible-galaxy collection install --force -p $(COLLECTION_INSTALL_DIR) $(COLLECTION_ARTIFACT)

lint: lint-yaml
	$(UV) run ansible-lint

lint-yaml:
	git ls-files -z -- '*.yml' '*.yaml' | xargs -0 $(UV) run yamllint

# The contract tests use only the Python standard library for portability.
test: collection-install
	$(UV) run python -m unittest discover -s tests -p 'test_*.py'

molecule: collection-install
	$(UV) run molecule test -s default

molecule-persistence: molecule-persistence-version-only

molecule-persistence-version-only: collection-install
	OPENHANDS_CHECKSUM_MODE=version-only $(UV) run molecule test -s persistence

molecule-persistence-verified: collection-install
	OPENHANDS_CHECKSUM_MODE=verified $(UV) run molecule test -s persistence

check: lint test molecule

release-patch:
	./scripts/release.sh patch

release-minor:
	./scripts/release.sh minor

release-major:
	./scripts/release.sh major
