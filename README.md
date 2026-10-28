# Smash Wii U Hidden Fighter CSS Expansion

> **Known boot failure (2026-10-28):** The seven-v2 build was reported to black-screen under Aroma SDCafiine. Neither original profile is a recommended working release. Structural checks did not establish game compatibility. Diagnostic testing is in progress.

Experimental **US SDCafiine** mod builder. Builds from your own game and update dump; no Nintendo assets are distributed here.

**Status:** archive and database checks pass. Console gameplay has not been tested. This is not a verified stable release. Final Smash forms have documented victory/results crashes; setting the UI victory flag to zero is only a fallback and does not fix their fighter code.

## Fighters

| Fighter | Character ID (decimal) | Cosmetic ID (decimal) | DB row (zero based) | CSS position (field 13) |
|---|---:|---:|---:|---:|
| Giga Bowser | 58 | 201 | 60 | 52 |
| Wario-Man | 59 | 60 | 82 (added) | 53 |
| Giga Mac | 60 | 202 | 61 | 54 |
| Mega Lucario | 61 | 62 | 83 (added) | 55 |
| Fighting Mii Brawler | 62 | 219 | 73 | 56 |
| Fighting Mii Swordfighter | 63 | 220 | 74 | 57 |
| Fighting Mii Gunner | 64 | 221 | 75 | 58 |

`forms` enables four forms. `seven` additionally enables the three enemy Miis. Each gets one costume (`c00`). CSS position is a group-relative value, not the database row or fighter ID. New slots use the non-DLC group; installed DLC remains unchanged. The ordinary Mii menu and Random entries remain intact.

Master Hand, Crazy Hand, Master Core, Ridley, Metal Face, Yellow Devil, Sandbag, Bomb and the other illustrated icons are excluded: the inspected UI rows contain invalid fighter ID `0xFFFFFFFF`. Icons do not supply fighter modules or player controls. Making these into fighters requires a separate engine/moveset project. This mod does not manufacture missing characters or unlock unowned DLC.

## Build

Requires Python 3.10+ and a decrypted, matching US game/update dump with `content/ls`, `dt00`, `dt01`, and `content/patch/`.

```sh
python tools/build.py --game "Games/Super Smash Bros/content" --update "Updates/Super Smash Bros/content" --profile forms --out build/forms
python tools/build.py --game "Games/Super Smash Bros/content" --update "Updates/Super Smash Bros/content" --profile seven --out build/seven
python -m unittest discover -s tests -v
```

The current baseline is the 82-row US database, paired with the update's own resource tables. Title IDs, donor IDs, reserved rows and database dimensions are checked before edits. This rejects several incompatible/previously edited inputs; it is not a universal version compatibility guarantee. Outputs must be fresh directories. Original dumps are read only.

## Install

Use just one generated pack at a time.

Legacy SDCafiine:

```text
SD:/sdcafiine/0005000010144F00/HiddenForms-Experimental/content/patch/
SD:/sdcafiine/0005000010144F00/HiddenSeven-Experimental/content/patch/
```

Aroma SDCafiine plugin:

```text
SD:/wiiu/sdcafiine/0005000010144F00/HiddenForms-Experimental/content/patch/
SD:/wiiu/sdcafiine/0005000010144F00/HiddenSeven-Experimental/content/patch/
```

Copy the generated `sdcafiine` folder to the SD root for legacy loading, or place its title-ID folder under `wiiu/sdcafiine` for Aroma. Enable SDCafiine and select the pack when launching the US game. Do not merge packs or combine with another CSS/resource-table mod. Disable this pack and restart to restore stock behavior. No console files are overwritten.

The output contains rebuilt compressed `resource*` tables, a merged `patchlist`, and complete replacements for each affected `packed` archive. Loose `ui_character_db.bin` files alone are not an SDCafiine build. All four resource partitions (`data`, `data(us_en)`, `data(us_fr)`, `data(us_sp)`) are handled. Existing archive members stay at their original offsets; new/replaced data is appended. SHA-256 hashes and exact slot edits are in `BUILD-REPORT.json`.

## Limits and assumptions

- Test offline local versus/training first. Results, respawn, CPU AI, entry, items and transformations can fail; see [validation checklist](docs/VALIDATION.md). Eight-player and other modes are unverified.
- UI reuses matching ordinary-fighter portraits/nameplates, including normal Mii portraits where enemy assets are absent. These are fallback pictures, not the custom art in the reference screenshot. No custom text or runtime patch is claimed.
- Cosmetic IDs 201/202 and 219–221 come from the supplied database. Wario-Man 60 and Mega Lucario 62 use the CSS editor's documented cosmetic mapping. Filename variants follow inspected executable strings; aliases cover the observed capitalization differences. Rendering still needs hardware confirmation.
- Existing hidden rows 60/61 and 73–75 are reused. Wario-Man and Mega Lucario lack database rows, so two rows are appended; no boss/item placeholders are overwritten.
- Victory field 5 is set to zero for fallback UI. Missing results motions, specializer logic and Final Smash state requirements are not repaired. A winning team workaround reported in old tutorials is not a stability guarantee.

## Public repository contents

Publish source, tests, documentation and the source-only ZIP. Keep dumps, decrypted executable sections, research downloads and generated SDCafiine archives private. `.gitignore` excludes them; `tools/package_source.py` additionally uses an explicit file allowlist and scans its output for local paths and credential-like material. Publishing under a GitHub account necessarily exposes that account's public identity; source files contain no private email, local user path or dump contents.

See [sources](docs/SOURCES.md). No third-party binaries, firmware, keys, executables or copyrighted game files are included in the public package.
