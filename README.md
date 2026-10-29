# Smash Wii U hidden CSS expansion — US v304

Work in progress. **A complete stable mod has not been achieved.** Original seven-v2 fails to boot on Aroma; probe04 and candidate06 fail while entering CSS. Do not install those builds.

Candidate07 uses official Sm4shExplorer 0.07.4 packing, seven existing rows and executable-verified cosmetic names. It corrects candidate06's partial language packs: shared portraits are imported once into data, while genuinely localized UI stays in its native partition. The user confirmed CSS loading and Giga Bowser Training in Cemu. An experimental, separately built Giga-only Aroma companion now addresses the observed KO conversion in the equivalent Cemu engine probe; it is not hardware validated. Results, UI rendering, other fighters and console behavior still require investigation.

## Candidate roster

| Fighter | Fighter ID | Cosmetic ID | DB row | CSS position |
|---|---:|---:|---:|---:|
| Giga Bowser | 58 | 201 | 60 | 52 |
| Wario-Man | 59 | 203* | 62 | 53 |
| Giga Mac | 60 | 202 | 61 | 54 |
| Mega Lucario | 61 | 204* | 63 | 55 |
| Fighting Mii Brawler | 62 | 219 | 73 | 56 |
| Fighting Mii Swordfighter | 63 | 220 | 74 | 57 |
| Fighting Mii Gunner | 64 | 221 | 75 | 58 |

All numbers are decimal and rows are zero based. CSS position is field13, distinct from fighter ID and database row. *203/204 repurpose Question/sh_all placeholder cosmetics; these are valid native names, not dedicated Wario-Man/Mega Lucario cosmetic mappings. Other menus using generic artwork may be affected. IDs60/62 previously used as cosmetics are absent from this executable's mapping table and were incorrect.

The 82-row database, normal fighter rows, Random and normal Mii menu remain intact. Each added fighter uses c00. Portraits and nameplates are ordinary-fighter placeholders, not completed custom artwork. Boss/item icons whose fighter ID is 0xFFFFFFFF do not provide controllable fighter modules and are excluded.

## Rebuild locally

Requires a matching decrypted US v304 base/update dump and the official [Sm4shExplorer 0.07.4 release](https://github.com/thefungus/Sm4shExplorer/releases/tag/0.07.4). Keep all game data and generated archives private.

1. Place the owned base/update content under `Games/Super Smash Bros` and `Updates/Super Smash Bros`.
2. Run `python tools/prepare_native_candidate.py` once against fresh output paths. It validates the native cosmetic table and generates a private exporter manifest and 126 inputs. Optional `--out`, `--manifest` and `--report` select fresh paths for another build.
3. Provide Sm4shExplorer a merged game view: base content dt00/dt01/ls, the update patch directory and update metadata. The wrapper opens this view read only.
4. Run `tools/export_with_sm4shexplorer.ps1` using **32-bit Windows PowerShell**, passing `-ExporterExe`, `-GameRoot`, a fresh `-WorkRoot`, and `-Manifest .private/official-inputs.json`.
5. Run `python tools/verify_official_candidate.py --patch <official-export>/content/patch`.
6. Run `python tools/package_official_candidate.py --patch <official-export>/content/patch`.
7. Run `python -m unittest discover -s tests -v` and `python tools/package_source.py`.

The legacy custom-export CLI is disabled. Old probe scripts remain for historical reproduction; they are not a release workflow. The old verifier describes that retired format and must not be used to certify candidate06.

## Aroma SDCafiine layout

```text
SD:/wiiu/sdcafiine/0005000010144F00/07-HiddenSeven-SharedUI/content/patch/
```

The private candidate ZIP contains this directory tree. Use one pack at a time; do not merge its resource tables with older probes or other CSS mods. This candidate is for offline investigation, not a stable release. The user confirmed Giga Bowser gameplay in probes02/03, but death reverts to Bowser and results can softlock. Candidate07 does not claim to repair these fighter lifecycle issues.

## Findings and validation

See [native findings](docs/NATIVE-FINDINGS.md), [failed UI audit](docs/UI-FAILURE-AUDIT.md), [test record](docs/VALIDATION.md) and [sources](docs/SOURCES.md). Offline checks compare imported bytes and affected archive members; they do not establish console stability.

The [experimental Giga Bowser respawn companion](docs/RESPAWN-COMPANION.md) is a separately built WUPS plugin with narrow US-v304 code signatures. It is not bundled with the SDCafiine candidate and has no console validation.

Public distribution is restricted to source, synthetic tests and documentation. The explicit allowlist and privacy scanner in `tools/package_source.py` exclude dumps, game scripts, decrypted executables, tool downloads, local paths and generated Nintendo assets. No game-data ZIP belongs in this repository.
