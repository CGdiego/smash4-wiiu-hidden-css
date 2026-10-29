# US v304 native-code findings

These findings come from the user's local update executable and MSC files. No executable, disassembly, game script or Nintendo asset is included in the public source repository.

## Confirmed cosmetic mapping error

The executable's key/name table at virtual address `0x1033BE70` maps cosmetics 201 to `Koopag`, 202 to `Littlemacg`, 203 to `Question`, 204 to `sh_all`, and 219/220/221 to `Miienemyf`/`Miienemys`/`Miienemyg`. It has **no mappings for cosmetics 60 or 62**. The original builder relied on generic editor labels for Wario-Man and Mega Lucario; those labels do not establish mappings in this executable. That implementation was wrong.

The new candidate preparer validates this table directly, with known key/name guards and a sentinel. It reuses existing placeholder rows 62/63 with cosmetics 203/204 for Wario-Man/Mega Lucario rather than inventing mappings. This preserves the 82-row database and normal fighter rows, but repurposes generic Question/sh_all cosmetics; other menus using those generic images may be affected. It is an experimental tradeoff, not a universal compatibility claim.

## Transformation logic is not just UI metadata

Native helper routines beginning at `0x030BF9C0` and `0x030C1FDC` explicitly map the four forms back to their base fighter kinds: 58→15, 59→22, 60→41, 61→30. A nearby native object-initialization path around `0x02E4567C` also pairs base and transformed kinds. These routines were not patched. Their presence does **not** establish which specific call site runs on death; several callers appear to be resource lookup paths. Patching these helpers globally could alter legitimate Final Smashes and resource loading.

Using [jam1garner's pymsc](https://github.com/jam1garner/pymsc), the first 2,239 MSC scripts in Bowser and Giga Bowser were compared by opcode, push-bit and operands. They are identical, including the common Dead/Rebirth registrations. This rules out a simple differing instruction in those common scripts; it does not prove the native helpers above cause the observed respawn. Fighter-specific initialization and native state still need tracing. The source research used [MSC syscall documentation](https://github.com/Just-Stabb/Smash4ModdingTests/tree/HEAD/reference/msc-note-sheet) as a navigation aid and checked candidate native code against the actual update.

## Missing results assets cannot safely be replaced blindly

The resource table has Bowser entry/results animation paths but no corresponding Giga Bowser entry/results paths. Extracted skeleton files also differ in size between base and transformed forms: Bowser/Giga Bowser 8876/8204 bytes, Wario/Wario-Man 12348/9548, Little Mac/Giga Mac 5404/5964, Lucario/Mega Lucario 7308/9100. Size differences alone do not prove animation incompatibility, but they invalidate any assumption that a blind copy is automatically safe. No retargeting or victory fix is claimed.

## Corrected export workflow

The official [Sm4shExplorer 0.07.4 release](https://github.com/thefungus/Sm4shExplorer/releases/tag/0.07.4) is loaded as a local .NET assembly in a 32-bit Windows PowerShell process. Its existing workspace import and packed export routines are used instead of the custom record insertion that failed in test04. Tool binaries, logs, merged input links and generated game archives remain private. The source-only wrapper refuses an existing export work root so the tool cannot clean a previous workspace by accident.

The candidate uses one executable-defined spelling per UI asset and assigns separate embedded NUT texture IDs, checked against the native fighter-UI headers. Only GIDX metadata changes; no image pixels are edited. [Smash Forge's NUT format implementation](https://github.com/jam1garner/Smash-Forge/blob/master/Smash%20Forge/Filetypes/Textures/NUT.cs) establishes that GIDX stores the texture HashId. Whether the newly assigned UI identities render as intended remains a runtime question.

## Release gate

### Candidate06 CSS crash: partial language packs

The user reproduced a CSS-loading crash in Cemu. Its private log identifies the ResourceSystem reading thread and the path `data(us_en)/ui/replace/chr/chr_10/packed`. The native shared portrait pack is 3,846,460 bytes; candidate06 rebuilt data to 4,217,100 bytes but also created an English pack of only 371,085 bytes containing new UI assets. Existing ordinary portrait records still referenced offsets in the shared pack. The reading call's logged count was `0xFFF077CA`, consistent with an invalid size calculation; attributing that exact calculation to a particular record remains an inference.

The preparer incorrectly treated inherited child bit0x800 as proof of physical localization. The native packed folder record is decisive: for this English chr_10 folder it is 0x1604, without localization bit0x800. Candidate07 imports shared UI into data only and keeps language-specific imports only in native localized packs. This removes 190 redundant imports. The verifier now rejects new localized packs that shadow originally shared folders and checks each exported packed file's length against its folder record. Candidate06 fails this regression check. The user confirmed that candidate07 loads CSS and Giga Bowser Training in Cemu; the respawn bug remains.

A separate private Cemu-only experiment changes the alternate-kind assignment at 0x02E4570C from15 to58. The surrounding instruction signature and module CRC0x63FAA900 are checked before the experiment. It changes no dump files or SDCafiine content. This is a hypothesis test, not a Wii U runtime patch or a proven fix; ordinary Bowser Final Smash behavior would also require regression testing before any deployment.

A complete stable release has **not** been achieved. Cemu CSS and Giga Training pass; required gates remain: Wii U boot/CSS, correct UI, persistent respawn, animation/voice/results loading, other hidden fighters, rematches and ordinary-roster regression testing. The native mapping findings are investigation targets, not deployable binary patches. A CSS-only seven-slot archive must not be presented as solving the fighter lifecycle.
