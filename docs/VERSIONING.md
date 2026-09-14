# Versioning policy

HappyMeasure separates the **internal source-build identity** from the **public release decision**.

## Internal build version

During active development the runtime/package version uses a PEP 440 beta serial such as:

```text
1.1b7
1.1b8
1.1b9
```

Every commit must increment the beta serial by exactly one relative to its first parent. `src/keith_ivt/version.py` and `pyproject.toml` must match in the same commit.

Examples:

- parent `1.1b6` → next commit `1.1b7`;
- parent `1.1b7` → next commit `1.1b8`;
- a bug-fix-only commit still increments the internal build number;
- documentation-only commits also increment it.

The CI version-policy gate checks the whole pushed/PR commit range, not just final HEAD, so multiple unnumbered commits cannot be hidden behind one final bump.

## Public release version

The public release name/tag is chosen deliberately by a human after release validation. Internal build serials are not themselves a promise that a build will be published.

If release finalization intentionally changes the version line rather than continuing the current beta serial, that decision must be explicit in the release-finalization commit and the runtime/package/tag/artifact identity must be made consistent before publication. Do not silently rename a build after artifacts are produced.

## Published releases

- Never reuse a published tag/version for different source.
- Never replace a published artifact while pretending it is the same build.
- Build artifacts only from the exact commit selected for release.
- Record the selected tag/version and artifact hashes in the final GitHub Release record.

## Source of truth

- runtime identity: `src/keith_ivt/version.py`
- package identity: `pyproject.toml`
- policy enforcement: `tools/release/check_version_sequence.py` and CI

Current operational docs intentionally avoid hardcoding the latest internal serial so they do not become stale on every commit.
