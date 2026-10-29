# UI failure audit, 2026-10-29

Working baseline: user-tested test03. Test04 boots but hangs with buzzing while entering CSS.

Test04 introduced multiple unvalidated changes together: 22 new native resource records per partition, an extra 8192-byte name block per partition, external override flags copied from existing patched-file conventions, two capitalization variants, and patchlist additions. It kept packed archive data unchanged. Preserving old records proved insufficient for game compatibility; the Python parser accepting an output does not validate the game loader. Comparison with original tables and Sm4shExplorer's source has not identified a proven cause.

Test05 isolates the portrait lookup with a different, smaller change. It renames only the existing `chr_10_Koopa_01.nut` resource reference to `chr_10_Koopag_01.nut`, storing that name in verified unused zero padding inside the existing string block. The same packed texture bytes remain at the same offset. It preserves record count/order, existing extension table location, file sizes, flags, patchlist and all archive data from test03. Assertions verify the new name remains between its native neighboring paths. This is a temporary transfer: normal Bowser's portrait can become blank. It is not a final UI implementation.

Acceptance: reach CSS; identify whether the extra slot gets normal Bowser artwork; load/exit Training. Failure at CSS would implicate the isolated name/reference change or game lookup assumptions; do not infer a particular cause without more evidence. A loaded CSS with a still-blank extra slot would mean the assumed lookup name/category needs investigation.

Only after this isolated path works: restore Bowser's portrait, add a dedicated Giga portrait through a validated resource workflow, then test nameplates separately. Respawn persistence and results animation/loading work remain gated on UI loading; no fix for either is claimed.
