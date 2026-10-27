"""Verify shipped native artifact and run actual Win32 forwarding regression."""
from pathlib import Path
import hashlib
import json
import subprocess

root = Path('work/reframework-window-fix')
info = json.loads((root/'runtime-artifact.json').read_text(encoding='utf-8'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
assert sha(root/'dinput8.dll') == info['FixedHash']
assert sha(Path('launcher/dependencies/REFramework/dinput8.dll')) == info['FixedHash']
assert sha(root/'hook_test.exe') == info['TestBinaryHash']
for name, expected in info['TestInputs'].items():
    assert sha(root/name) == expected, name
for name in ['WindowsMessageHook.hpp', 'WindowsMessageHook.cpp']:
    folder = 'upstream-src' if name.endswith('.cpp') else 'patched-src'
    assert (root/'tests'/name).read_text(encoding='utf-8') == (root/folder/name).read_text(encoding='utf-8')
for folder, name in [('upstream-src', 'legacy_initialize'), ('patched-src', 'initialize')]:
    source = (root/folder/'REFramework.cpp').read_text(encoding='utf-8')
    start = source.index('bool REFramework::initialize_windows_message_hook() {')
    end = source.index('// Ran on the first valid frame', start)
    exact = source[start:end].replace('REFramework::initialize_windows_message_hook', 'TestFramework::'+name)
    assert exact in (root/'tests/extracted-initializers.inc').read_text(encoding='utf-8')
source = (root/'patched-src/REFramework.cpp').read_text(encoding='utf-8')
monitor = source[source.index('void REFramework::hook_monitor()'):source.index('typedef struct _LDR_DLL')]
assert 'm_windows_message_hook->is_valid_for(m_wnd)' in monitor
assert info['ExportCount'] == 1472
result = subprocess.run([str((root/'hook_test.exe').resolve())], capture_output=True, text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
assert result.returncode == 0, result.stdout+result.stderr
print(result.stdout.strip())
print('PASS: pinned native artifact, exact extracted initializer and watchdog guard, matching export ABI')
