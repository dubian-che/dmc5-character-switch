REFramework local Windows message chain fix (MIT)
Upstream: https://github.com/praydog/REFramework
Base commit: d4611aef1d63effd3a736bdf9404ea702428017d
Local changes: src/WindowsMessageHook.hpp and src/REFramework.cpp only.
Valid registrations are preserved across watchdog/first-frame reinitialization;
external subclasses are never captured as a replacement original procedure.
Fixed DLL SHA256: CBA7C25F57D199E2FDFB73EB3BA8BA5BAF028D453D428498796E85FBDD75CB0F
Original DLL SHA256: CB1ACC11BE71184BE1EB5C29CCEA2DB156A55EEE861686B71BBC522865D2C98A
Patch, tests and original sources: work/reframework-window-fix/
Original release-39 backup: work/checkpoints/release-39-before-window-hook-fix/
This is a local source rebuild, not an upstream official binary.
The main launcher still preserves existing loaders. For this exact baseline use
scripts/Install-WindowHookFix.ps1 (closed game required; hash checked; backed up).
