# Security and privacy

This repository contains source code, synthetic tests and documentation only. It
must not contain Nintendo game data, decrypted executables, emulator profiles,
private logs, credentials or generated SDCafiine packs.

## Sensitive-data rules

- Never commit passwords, tokens, API keys, private keys, certificates, dump
  files, decrypted binaries or save data.
- Do not include absolute local paths, Windows usernames, hardware identifiers,
  emulator directories or controller profiles in reports.
- Preserve intentional project attribution and public contributor identities.
- Keep owned game content and tool downloads outside this repository.
- Treat every generated archive as private unless it contains only the
  source-only allowlist.

The public packaging command is an allowlist, not a general directory archive:

```powershell
python tools/package_source.py --out dist/smash4-css-source.zip
```

Inspect the ZIP contents before sharing it. The scanner rejects common private
path and credential patterns, but a human review is still required for new
file types and diagnostic output.

## Release privacy checklist

1. Run the unit tests and the source packager from a clean checkout.
2. Inspect `git status --short` and the complete staged diff.
3. Check that generated archives, dumps, logs and emulator data are outside the
   repository and outside any handoff bundle.
4. Search new text files for usernames, absolute paths, tokens, private keys and
   save locations.
5. Confirm that the source ZIP contains only the explicit allowlist.
6. Publish source and documentation, never a game-data ZIP.

If sensitive material is discovered in a commit, stop distribution and identify
the affected refs. Remove the material from every reachable commit using an
approved history-rewrite procedure, coordinate the force-push with repository
owners, and rotate any exposed credential. Do not rewrite history merely to
change intentional authorship or public contributor attribution.

## Reporting

Do not open a public issue with sensitive evidence. Contact the repository
maintainers privately, describing the affected path, commit and exposure
without attaching game data or credentials.
