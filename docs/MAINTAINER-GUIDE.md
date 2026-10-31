# Maintainer guide

## Scope and trust boundaries

The public repository is a source-only implementation. It reads a user's own
Smash Wii U files locally, edits selected resource/parameter records, and
writes a private SDCafiine candidate. The repository does not provide a game
dump, decrypted executable, proprietary archive, emulator configuration or
binary plugin.

There are three deliberately separate layers:

1. `tools/smash4.py` contains lossless readers and resource-table helpers.
2. `tools/build.py` and the official-export scripts transform private input
   data into a candidate pack.
3. `tools/verify_*.py` and `tests/` reject malformed mappings, unsafe paths,
   resource-table regressions and accidental disclosure.

The optional `companion/main.c` is a separately built, narrowly guarded
experiment. It is not part of the SDCafiine candidate.

## Data flow

The official candidate path is:

```text
owned base/update dump
        |
        v
prepare_native_candidate.py
        |
        v
private manifest and inputs
        |
        v
Sm4shExplorer 0.07.4 export wrapper
        |
        v
verify_official_candidate.py
        |
        v
package_official_candidate.py
        |
        v
private SDCafiine ZIP
```

The source packager follows a different path and must never discover files by
walking the parent directory. `tools/package_source.py` uses an explicit
allowlist so dumps and generated outputs cannot enter the public ZIP by
accident.

## Mapping invariants

The current candidate preserves the original 82-row database. It replaces only
the seven validated reserved rows and uses existing donor rows for the field
schema. Fighter ID, cosmetic ID, database row and CSS field 13 are distinct
values; changing one does not imply the others.

Cosmetic IDs 203 and 204 intentionally reuse native `Question` and `sh_all`
placeholders. This is a compatibility tradeoff, not proof that dedicated
Wario-Man or Mega Lucario UI identities exist. The Mii enemy rows are also
known to be enemy-oriented actors, not full retail fighters.

Resource localization is determined by the packed-folder record. Inherited
child flags do not prove that a language partition owns a physical copy.
Adding a partial localized pack can cause invalid offsets or CSS-loading
failures, so shared assets belong in the shared `data` partition unless native
folder ownership proves otherwise.

## Experimental status

The current candidate has evidence for CSS loading and Giga Bowser Training in
Cemu, but it does not pass the stable-release gate. Known failures include
fighter conversion after KO, incomplete results/animation behavior and
unverified console behavior for the full roster. Do not describe a CSS-only
candidate as fixing fighter lifecycle code.

The companion changes one guarded native assignment for US v304 only. It must
remain inactive when title, version, module bounds or instruction signatures
do not match. It has no hardware validation and must not be bundled with the
CSS pack.

## Handoff checklist

1. Start with [README](../README.md), then read [VALIDATION](VALIDATION.md).
2. Check [NATIVE-FINDINGS](NATIVE-FINDINGS.md) before interpreting a new result.
3. Reproduce with a clean private dump and a fresh export directory.
4. Run all Python tests and the source-only privacy packager.
5. Record test environment, title/update version, language and profile without
   recording personal paths or hardware identifiers.
6. Update documentation when a hypothesis becomes confirmed or is rejected.
7. Keep private candidate ZIPs outside the public repository.
