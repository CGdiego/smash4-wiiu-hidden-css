# Experimental Giga Bowser respawn companion

`companion/main.c` is a separate Aroma WUPS plugin, not an SDCafiine file replacement. It targets only the US title `0005000010144F00`, update v304, and only the engine path that assigns ordinary Bowser (15) as the alternate form for Giga Bowser (58). After the original initializer runs, it changes that alternate back to 58.

It has guardrails: title/version selection, `cross_f.rpx` text bounds, and the exact four-word US v304 signatures at both the initializer and the assignment site. It remains inactive if any guard fails.

This was validated only by the equivalent one-instruction Cemu investigation: changing the native alternate assignment from Bowser to Giga Bowser kept Giga Bowser after a KO. It is **not hardware validated**. It does not fix results, entry animation, portraits/nameplates, Wario-Man, Giga Mac, Mega Lucario, or the enemy-Mii forms.

## Build and use

Build from source with the pinned/current official WUPS and FunctionPatcher SDK sources, plus devkitPro, for example:

```powershell
.\tools\build_companion.ps1 -WupsRoot <WUPS SDK root> -FunctionPatcherRoot <FunctionPatcher SDK root>
```

The generated `.wps` needs Aroma's WUPS support and the separately installed FunctionPatcherModule/WUMS prerequisites documented by the FunctionPatcher project. Do not install it alongside unknown engine-patching plugins. Back up the SD card, use the US v304 game only, and remove the plugin immediately after a hang or unexpected behavior.

No binary plugin or Nintendo data is committed or included in the source ZIP.
