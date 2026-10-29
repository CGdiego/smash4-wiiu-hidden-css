# Runtime validation still required

The original four/seven profiles have not passed runtime validation; seven-v2 produced an Aroma boot failure. Later probes were tested by the user on a US Wii U with Aroma SDCafiine:

- 00 StockControl: boot and CSS passed.
- 01 MarioSevenCostumes: boot and CSS passed.
- 02 GigaBowser in BowserSlot: Training loading/control passed; death restores Bowser.
- 03 SeparateSlot: extra slot selects playable Giga Bowser. Icon is white and name missing. Death restores Bowser; a subsequent win produced a T-pose and results softlock.
- 04 UI probe: user confirmed boot, followed by a freeze with buzzing audio while loading CSS. Do not use. It added 88 external UI overrides across four partitions. Root cause is not established.
- 05 SinglePortrait: built, awaiting console testing. Temporarily reassigns normal Bowser's existing CSS portrait record to Giga Bowser. No new records, external flags, name blocks, nameplates or aliases. Normal Bowser may have a blank icon during this diagnostic. All packed files and patchlist remain identical to test03. Respawn/results are unchanged.

The assistant has not run gameplay locally. Neither original profile nor any probe is a stable release.

Start with a clean US game and only this pack. Record game update, SDCafiine version, active language and profile. Test each hidden fighter separately before testing combinations.

- Open/reopen CSS and move every player cursor over all additions.
- Select each addition, cancel, reselect, start training and a normal local match.
- Confirm the selected fighter, costume, controls, model, portraits and nameplates.
- Test entry, all movement/attacks, shielding/grabs/items, KO, respawn, match exit, loss and win.
- Test timeout, sudden death, individual and team results, rematch and return to CSS.
- Test CPU as each addition and combinations of different hidden fighters.
- Test the original roster, DLC actually installed, Random and the normal Mii menu.
- Repeat US English/French/Spanish before claiming language support.

Known research limitations: Final Smash forms may freeze upon winning because standalone fighter results behavior is incomplete. Enemy Miis are multi-man actors, not full retail fighters. UI victory fallback does not repair gameplay code. Avoid saving/relying on replays until validated. Eight-player, Classic, All-Star, Tour, Orders, amiibo and network play are outside the supported test scope.

If a case fails, disable the pack, restart and compare stock behavior. Do not assume a different icon or another enabled flag fixes the fighter module. A stable release requires actual runtime evidence and potentially engine/animation work beyond CSS parameters.
