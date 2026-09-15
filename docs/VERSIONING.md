# Versioning policy

HappyMeasure separates normal development build numbering from an explicit human release freeze.

## Normal development builds

Outside a release freeze, the runtime/package version uses a PEP 440 beta serial such as:

```text
1.1b7
1.1b8
1.1b9
```

Every normal development commit increments the beta serial by exactly one relative to its first parent. `src/keith_ivt/version.py` and `pyproject.toml` must match in the same commit.

The CI version-policy gate checks the whole pushed/PR commit range, not just final HEAD, so multiple unnumbered commits cannot be hidden behind one final bump.

## Active 1.2b release freeze

The human release owner selected **1.2b** before the final screenshot/package pass. While `tools/release/RELEASE_FREEZE_MARKER` exists, its value is the required runtime/package identity for every commit.

For the current release window:

```text
1.2b
```

remains fixed across screenshot refreshes, documentation changes, packaging adjustments, and release-only fixes. This keeps the version shown in screenshots identical to the intended public release identity.

Entering or changing a release freeze requires `[release-version]` in that commit message. Once a freeze is active, subsequent commits must preserve the exact frozen version; they do not increment a beta serial.

The freeze ends only after that release is published. The first post-release development commit removes `tools/release/RELEASE_FREEZE_MARKER` and resumes the normal per-commit beta serial sequence on the next development line.

## Published releases

- Never reuse a published tag/version for different source.
- Never replace a published artifact while pretending it is the same build.
- Build artifacts only from the exact commit selected for release.
- Record the selected tag/version and artifact hashes in the final GitHub Release record.

## Source of truth

- runtime identity: `src/keith_ivt/version.py`
- package identity: `pyproject.toml`
- active release freeze: `tools/release/RELEASE_FREEZE_MARKER`
- policy enforcement: `tools/release/check_version_sequence.py` and CI
