# Versioning policy

HappyMeasure uses PEP 440-compatible prerelease versions for Python/package metadata and matching `v<version>` Git tags.

## Format

Current beta examples:

```text
Python/package: 1.1b6
Git tag:        v1.1b6
Prose:          1.1 beta 6
```

Do not reuse a published version/tag for different source. If `v1.1b5` is already public, any later behavior change must have a new version such as `1.1b6`.

## Meaning

- `aN`: alpha/development validation build.
- `bN`: beta build for broader testing while UI/hardware behavior may still change.
- `rcN`: release candidate with blocker-only changes expected.
- `.postN`: packaging/documentation-only correction to an otherwise identical release; do not use it for behavior changes.

## When to increment

- Increment the beta/alpha serial for another prerelease within the current feature line.
- Increment minor/major when product scope or compatibility policy warrants it.
- Never overwrite/rebuild an already published tag as though it were the same release.
- Keep runtime metadata, `pyproject.toml`, README, changelog, release checklist, release notes and artifact names consistent.

## Current baseline

`1.1b6` is the current source/release candidate. It remains a beta until the automated source/Qt gates, Windows desktop/package smoke, and selected staged hardware validation are complete. See `VALIDATION_STATUS.md` for the current gate rather than recording test state here.
