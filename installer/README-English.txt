DMC5 Character Switch 1.0.0 - desktop GUI revision

Extract the complete archive and run DMC5SwitchLauncher.exe (00-Setup.cmd opens the same UI).
Select the game folder, then click Install / Update. Exit the game first.
Use the Chinese / English button in the top-right corner to switch languages instantly.
Configure all five keyboard shortcuts and Taunt + controller combinations in the same window, then click Save bindings. Restart the game to apply.
Existing bindings are loaded and preserved. New-install defaults: F5/F6/F7/F8/F9.
Export diagnostics, Restore previous files and Launch game are available in the same UI.
Keep Engine.ps1, Language.ps1, manifest.json and payload next to the EXE; do not copy the EXE alone.
The verified 3S, audio pool, DSD charge, summoned-sword, EX costume and World of V fixes are preserved.
The installer validates the tested game executable before writing files, and backs up replaced files.

Start from Steam. Do not reinstall through the old launcher, which contains older files.
New-install keys: F5 next, F6 previous; F7 Nero, F8 Dante, F9 Vergil.
Delete opens 3S; Insert opens REFramework; F10 marks diagnostic records.
Do not enable Graphics / Hide GUI in REFramework, as it hides game menus.
Default controller: Taunt + LB previous, Taunt + RB next. Existing bindings take priority.

For a bug, press F10, pause if possible, then click Export diagnostics to export a ZIP to Desktop before restarting.
Diagnostics contain logs, character state, bindings and hashes, but no saves or full memory dumps.
Logs may contain local paths and usernames. Review them before sharing. Nothing is uploaded automatically.
Restoration stops if installed files were subsequently changed, to protect those changes.

Includes costume-1: reserve characters use the native character-selection costume.
Includes dante-round-trip-1: initializes the missing DSD style-charge channel on first load, without cycling weapons or resetting the existing sheath charge.
The first-load move fix was verified in game with diagnostics; costume preservation has preliminary user confirmation.
Test status: startup, 3S menu, switching, audio pool, Dante charge and Palace V cleanup were tested locally.
Not every 3S feature or mod combination has been validated. An intermittent M3 results crash remains unresolved.
Licenses and source changes are included. No personal saves or logs are bundled.
