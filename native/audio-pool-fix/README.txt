DMC5 Wwise default sound-pool fix, 2026-11-05

The M3 full-party trace measured pool 2 at 99.94% occupancy and 72 failed allocations, including 45 playback-instance allocations. The DLL expands only the verified default SoundEngine pool creation from 10 MiB to 32 MiB. The native pool ID, block size, alignment, other pools and larger native budgets are preserved.

winmm.dll forwards all 181 original Windows multimedia exports. The EXE image size, pool creation prologue and default-pool call site are checked before hooking. Unknown EXE signatures keep forwarding Windows APIs without patching the game.

The root dinput8.dll and all Lua gameplay fixes are unchanged. No diagnostic event logger is included in this DLL.

Sources, verified export/header snapshots and MinHook 1.3.4 sources/license are included. The currently included binary is the gameplay-validated candidate.

Rebuild with scripts/Build-AudioPoolFix.ps1 (Visual Studio x64 tools required); -NoDeploy builds/tests without replacing the gameplay-validated prebuilt DLL. The normal launcher build embeds the prebuilt DLL.
