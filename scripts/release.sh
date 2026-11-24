#!/bin/sh
set -eu

fail() {
    printf 'release: %s\n' "$*" >&2
    exit 1
}

check_repository() {
    branch=$(git symbolic-ref --quiet --short HEAD) || fail "HEAD is detached"
    [ "$branch" = "master" ] || fail "current branch is '$branch', expected 'master'"
    [ -z "$(git status --porcelain)" ] || fail "working tree is not clean"

    git fetch origin
    [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/master)" ] || \
        fail "local master does not match origin/master"
}

[ "$#" -eq 1 ] || fail "usage: $0 patch|minor|major"
bump=$1
case "$bump" in
    patch|minor|major) ;;
    *) fail "unknown version bump '$bump'" ;;
esac

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "not in a Git repository"
cd "$(git rev-parse --show-toplevel)"
check_repository

[ -f galaxy.yml ] || fail "galaxy.yml does not exist"
version=$(awk '
    $1 == "version:" {
        if (count++) exit 2
        value = $2
        gsub(/^"/, "", value)
        gsub(/"$/, "", value)
    }
    END {
        if (count != 1) exit 1
        print value
    }
' galaxy.yml) || fail "galaxy.yml must contain exactly one version field"
printf '%s\n' "$version" | grep -Eq \
    '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$' || \
    fail "galaxy.yml version must use MAJOR.MINOR.PATCH format"

major=${version%%.*}
remainder=${version#*.}
minor=${remainder%%.*}
patch=${remainder#*.}

case "$bump" in
    patch) patch=$((patch + 1)) ;;
    minor) minor=$((minor + 1)); patch=0 ;;
    major) major=$((major + 1)); minor=0; patch=0 ;;
esac
new_version="$major.$minor.$patch"
release_date=$(date +%F)

[ -f CHANGELOG.md ] || fail "CHANGELOG.md does not exist"
unreleased_count=$(grep -c '^## \[Unreleased\]$' CHANGELOG.md || true)
[ "$unreleased_count" -eq 1 ] || \
    fail "CHANGELOG.md must contain exactly one ## [Unreleased] heading"
if grep -Fq "## [$new_version] - " CHANGELOG.md; then
    fail "CHANGELOG.md already contains version $new_version"
fi

make check
check_repository

[ -z "$(git tag --list "$new_version")" ] || fail "tag $new_version already exists locally"
remote_tag=$(git ls-remote --tags origin "refs/tags/$new_version") || \
    fail "could not check remote tags"
[ -z "$remote_tag" ] || fail "tag $new_version already exists on origin"

printf '\nRelease preview\n'
printf '  Current version: %s\n' "$version"
printf '  New version:     %s\n' "$new_version"
printf '  Release date:    %s\n' "$release_date"
printf '  Branch:          master\n'
printf '  Commit:          Release %s\n' "$new_version"
printf '  Files:           galaxy.yml, CHANGELOG.md\n'
printf '  Tag:             %s (lightweight)\n\n' "$new_version"
printf 'Publish this release? [y/N] '
IFS= read -r answer
case "$answer" in
    y|Y) ;;
    *) printf 'Release cancelled.\n'; exit 0 ;;
esac

awk -v version="$new_version" '
    $1 == "version:" { $2 = "\"" version "\""; count++ }
    { print }
    END { if (count != 1) exit 1 }
' galaxy.yml > galaxy.yml.tmp || fail "could not update galaxy.yml version"
mv galaxy.yml.tmp galaxy.yml
awk -v heading="## [$new_version] - $release_date" '
    { print }
    $0 == "## [Unreleased]" { print ""; print heading }
' CHANGELOG.md > CHANGELOG.md.tmp
mv CHANGELOG.md.tmp CHANGELOG.md

git add -- galaxy.yml CHANGELOG.md
git commit -m "Release $new_version" -- galaxy.yml CHANGELOG.md
git tag "$new_version"

if ! git push --atomic origin master "refs/tags/$new_version"; then
    fail "push failed; commit and tag $new_version remain locally"
fi

printf 'Released %s.\n' "$new_version"
