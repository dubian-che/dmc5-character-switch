"""Install and roll back only in an isolated fake game directory."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile

script = Path('scripts/Install-WindowHookFix.ps1').resolve()
artifact = Path('work/reframework-window-fix')
info = json.loads((artifact/'runtime-artifact.json').read_text(encoding='utf-8'))
baseline = Path('work/checkpoints/release-39-before-window-hook-fix/launcher/dependencies/REFramework/dinput8.dll')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
with tempfile.TemporaryDirectory(prefix='dmc5-native-fix-test-') as tmp:
    game = Path(tmp)
    (game/'DevilMayCry5.exe').write_bytes(b'isolated installer fixture, never launched')
    store = game/'.dmc5-character-switch'; store.mkdir()
    manifest = store/'installed.json'
    dll = game/'dinput8.dll'; shutil.copy2(baseline, dll)
    def write_state(runtime_hash):
        manifest.write_text(json.dumps({'Files':[
            {'Path':'dinput8.dll','InstalledHash':runtime_hash,'Original':None,'OriginalTime':0},
            {'Path':'reframework/data/example.lua','InstalledHash':'future-script-state'}]}),encoding='utf-8')
    def run(rollback=False, ok=True):
        # Only this disposable test root is touched. Mock process discovery in
        # the child so a real game running elsewhere cannot block fixture IO.
        assert game.name.startswith('dmc5-native-fix-test-') and game.parent==Path(tempfile.gettempdir())
        quote=lambda s: "'"+str(s).replace("'", "''")+"'"
        command="function global:Get-Process { [CmdletBinding()]param([string]$Name); if($Name -ne 'DevilMayCry5'){throw 'Unexpected process query'} }; "
        command+='& '+quote(script)+' -GameRoot '+quote(game)
        if rollback: command+=' -Rollback'
        args=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-Command',command]
        result=subprocess.run(args,capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=30)
        assert (result.returncode==0)==ok, result.stdout+result.stderr
    write_state(info['PriorHash'])
    run(); assert sha(dll)==info['FixedHash']
    state=json.loads(manifest.read_text(encoding='utf-8-sig'))
    assert state['Files'][0]['InstalledHash']==info['FixedHash']
    record=store/'window-hook-fix/installed.json'
    first=record.read_bytes();run();assert record.read_bytes()==first
    # Rollback updates only the runtime record and preserves newer script data.
    state['Files'][1]['InstalledHash']='updated-after-runtime-fix'
    manifest.write_text(json.dumps(state),encoding='utf-8')
    run(rollback=True);assert sha(dll)==info['PriorHash']
    state=json.loads(manifest.read_text(encoding='utf-8-sig'))
    assert state['Files'][0]['InstalledHash']==info['PriorHash']
    assert state['Files'][1]['InstalledHash']=='updated-after-runtime-fix'
    run(rollback=True);run();assert sha(dll)==info['FixedHash']
    # Neither unrelated loaders nor inconsistent ownership may be overwritten.
    dll.write_bytes(b'unknown external loader');write_state(sha(dll))
    before=manifest.read_bytes();run(ok=False)
    assert dll.read_bytes()==b'unknown external loader' and manifest.read_bytes()==before
    shutil.copy2(artifact/'dinput8.dll',dll);write_state('wrong-owner-hash')
    run(ok=False);assert sha(dll)==info['FixedHash']
print('PASS: native fix install, verified backup, ownership, idempotence, rollback preserving later scripts, unknown-loader refusal; no real game files touched')
