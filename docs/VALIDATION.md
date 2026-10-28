# Runtime validation still required

Structural verification has passed; no Wii U or emulator gameplay was performed. Neither profile is promoted as stable.

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
