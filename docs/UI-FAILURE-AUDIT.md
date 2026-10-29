# UI failure audit, 2026-10-29

Working baseline: user-tested test03. Test04 boots but hangs with buzzing while entering CSS.

Test04 introduced multiple unvalidated changes together: 22 new native resource records per partition, an extra 8192-byte name block per partition, external override flags copied from existing patched-file conventions, two capitalization variants, and patchlist additions. It kept packed archive data unchanged. Preserving old records proved insufficient for game compatibility; the Python parser accepting an output does not validate the game loader. Comparison with original tables and Sm4shExplorer's source has not identified a proven cause.

Test05 isolates the portrait lookup with a different, smaller change. It renames only the existing `chr_10_Koopa_01.nut` resource reference to `chr_10_Koopag_01.nut`, storing that name in verified unused zero padding inside the existing string block. The same packed texture bytes remain at the same offset. It preserves record count/order, existing extension table location, file sizes, flags, patchlist and all archive data from test03. Assertions verify the new name remains between its native neighboring paths. This is a temporary transfer: normal Bowser's portrait can become blank. It is not a final UI implementation.

Acceptance: reach CSS; identify whether the extra slot gets normal Bowser artwork; load/exit Training. Failure at CSS would implicate the isolated name/reference change or game lookup assumptions; do not infer a particular cause without more evidence. A loaded CSS with a still-blank extra slot would mean the assumed lookup name/category needs investigation.

Only after this isolated path works: restore Bowser's portrait, add a dedicated Giga portrait through a validated resource workflow, then test nameplates separately. Respawn persistence and results animation/loading work remain gated on UI loading; no fix for either is claimed.

## Additional offline findings

The test04 output has **88 new resource records but only 44 physical loose texture files**. There are **44 pairs of case-only aliases** (`Koopag` and `KoopaG`). These cannot be represented as distinct files on the Windows workspace or a conventional FAT SD card. The second write targeted the same physical pathname. Both aliases are nevertheless registered in the game's resource tables and patchlist. This is a confirmed packaging ambiguity; it is not established as the specific instruction or loader failure behind the console freeze.

All 88 added resource references also reuse the donor's embedded NUT `GIDX` texture identity. For example, the chr_10 copies retain the Bowser ID `0x280015fe`; chr_13 retains `0x280052f6`; chrn_11 retains `0x28002102`. Each added texture is byte-identical to its donor. [Smash Forge's NUT parser](https://github.com/jam1garner/Smash-Forge/blob/master/Smash%20Forge/Filetypes/Textures/NUT.cs) reads this field into `HashId`, and its [NUT Editor documentation](https://github.com/jam1garner/Smash-Forge/wiki/NUT-Editor) exposes texture-ID assignment separately from filenames. Renaming a file does not change this identity. Whether the game accepts sharing these UI IDs or requires a new identity/reference mapping remains unverified; do not blindly assign arbitrary replacement IDs.

The builder now rejects case-insensitive path collisions before RF insertion, with regression tests for new/new and new/native collisions. A detailed local audit is saved at `build/test04-offline-audit.json` (not included in the public repository). Test05 avoids new physical texture copies, aliases, extra records and external flags; it remains untested and is not declared fixed.

No additional console test is requested while the Wii U is unavailable. A conclusive crash diagnosis still needs either loader/debugger evidence or later controlled console tests. The offline findings above are reproducible facts, not a claim that the results/respawn defects are repaired.
