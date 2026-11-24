# Repository instructions

## Changelog maintenance

Keep `CHANGELOG.md` current whenever work introduces a notable user-visible,
operational, security, compatibility, documentation, testing, CI, or developer
workflow change.

- Add entries beneath `## [Unreleased]` in the same change that implements the
  behavior.
- Use the Keep a Changelog categories `Added`, `Changed`, `Deprecated`,
  `Removed`, `Fixed`, and `Security`. Add only the subsections needed.
- Write concise descriptions of the effect on users or contributors; do not
  copy commit messages or list trivial formatting and internal refactoring.
- Clearly identify breaking changes, deprecations, removals, and security fixes.
- Do not manually create a released version section. The release script moves
  the Unreleased entries beneath the new version and date heading.
- Do not edit an existing released section except to correct inaccurate or
  missing information.

## CI status polling

When a GitHub Actions run is still in progress, wait at least 60 seconds between
status checks instead of repeatedly polling. Follow a different interval if the
operator requests one.

## Release ownership

Releases are the operator's responsibility. Agents must not run the release
Make targets or release script against this repository, create release commits
or tags, or push release commits or tags. Agents may maintain and test the
release tooling in isolated temporary repositories, but only the operator may
perform an actual release.
