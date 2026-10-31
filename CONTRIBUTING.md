# Contributing

The project is an experimental US v304 Smash Wii U CSS investigation. It is
not a stable release and does not redistribute game content.

## Before changing code

Read:

- [README](README.md) for the current release status and supported workflow.
- [Validation record](docs/VALIDATION.md) for known failures and required tests.
- [Native findings](docs/NATIVE-FINDINGS.md) before changing fighter mappings or
  lifecycle assumptions.
- [Security policy](SECURITY.md) before adding diagnostics, fixtures or assets.

Use a clean copy of the user's own base/update dump for local builds. Never
hard-code a local path or copy that dump into this repository.

## Development workflow

```powershell
python -m unittest discover -s tests -v
python tools/package_source.py
```

The private candidate workflow is intentionally separate:

```powershell
python tools/prepare_native_candidate.py --help
powershell -ExecutionPolicy Bypass -File tools/export_with_sm4shexplorer.ps1 -?
python tools/verify_official_candidate.py --help
python tools/package_official_candidate.py --help
```

Use fresh private output directories for each export. Do not use the legacy
custom exporter to certify a candidate.

## Change conventions

- Keep fighter IDs, cosmetic IDs, database rows and CSS positions explicit.
- Reject unsupported mappings instead of silently inventing or appending rows.
- Preserve unrelated resource entries byte-for-byte where the format permits.
- Add a regression test for every parser, path-collision or validation bug.
- Update the relevant findings and validation documents when evidence changes.
- Keep experimental probes separate from the candidate build and label them as
  unverified.

Before submitting a change, review the complete diff, run the tests, build the
source-only package, and verify that no generated game asset is tracked.
