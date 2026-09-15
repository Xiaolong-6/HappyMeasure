# Versioning policy

HappyMeasure separates normal development build numbering from an explicit human release freeze.

## Normal development builds

Outside a release freeze, the runtime/package version uses a PEP 440 beta serial such as:

```text
1.2b1
1.2b2
1.2b3
```

Every normal development commit increments the beta serial by exactly one relative to its first parent. `src/keith_ivt/version.py` and `pyproject.toml` must match in the same commit.

The CI version-policy gate checks the whole pushed/PR commit range, not just final HEAD, so multiple unnumbered commits cannot be hidden behind one final bump.

## Release freeze

The human release owner may select a public identity before the final screenshot/package pass. While `tools/release/RELEASE_FREEZE_MARKER` exists, its value is the required runtime/package identity for every commit in that release-finalization window.

A frozen identity may omit the normal internal beta serial, for example:

```text
1.2b
```

Entering or changing a release freeze requires `[release-version]` in that commit message. Once a freeze is active, subsequent release-only commits preserve the exact frozen version; they do not increment a beta serial.

## Post-release transition

The freeze ends only after the release is published. The first post-release development commit removes `tools/release/RELEASE_FREEZE_MARKER` and resumes normal numbered beta development.

If the frozen public identity is not itself a numbered beta serial, the transition commit uses `[release-version]` once to bridge back to the development sequence. For the published `v1.2b` release, development resumes at `1.2b1`; the next normal commit must then be `1.2b2`.

This override is a deliberate boundary transition, not permission to skip version increments during ordinary development.

## Published 1.2b baseline

- `v1.2b` was published on 2026-09-15 from commit `111337bb1aeb1927ab97922c616f767daf005a6e`.
- Both Windows portable release assets were produced by CI from that exact commit and independently re-downloaded with matching byte sizes and SHA-256 hashes.
- Post-release development resumes at `1.2b1`; the published tag and assets remain immutable.

## Published releases

- Never reuse a published tag/version for different source.
- Never replace a published artifact while pretending it is the same build.
- Build artifacts only from the exact commit selected for release.
- Record the selected tag/version and artifact hashes in the final GitHub Release record.

## Source of truth

- runtime identity: `src/keith_ivt/version.py`
- package identity: `pyproject.toml`
- active release freeze, when present: `tools/release/RELEASE_FREEZE_MARKER`
- policy enforcement: `tools/release/check_version_sequence.py` and CI
